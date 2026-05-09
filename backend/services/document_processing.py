import asyncio
import re
from io import BytesIO
from time import perf_counter
from typing import Callable, Optional

import pdftotext
from anyio import sleep
from pydantic import BaseModel

from backend.services.constants import CREATE_FACT_CHUNKS_SYSTEM_PROMPT, GET_MATCHING_TAGS_SYSTEM_PROMPT
from backend.services.cost_tracking import record_llm_usage
from backend.db import DocumentInformationChunks, DocumentTags, Documents, Tags, db, initialize_database
from backend.services.embeddings import get_embedding
from backend.services.openai_client import openai_client
from backend.services.utils import find


IDEAL_CHUNK_LENGTH = 4000


class GeneratedDocumentInformationChunks(BaseModel):
    facts: list[str]


class GeneratedMatchingTags(BaseModel):
    tags: list[str]


def get_retry_delay(error: Exception) -> float:
    retry_match = re.search(r"try again in ([\d.]+)s", str(error), re.IGNORECASE)
    if retry_match:
        return float(retry_match.group(1)) + 1
    return 5


async def generate_chunks(
    user_id: int,
    index: int,
    pdf_text_chunk: str,
    document_processing_job_id: Optional[int] = None,
):
    total_retries = 0
    while True:
        try:
            model = "llama-3.3-70b-versatile"
            started_at = perf_counter()
            output = await openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": CREATE_FACT_CHUNKS_SYSTEM_PROMPT},
                    {"role": "user", "content": pdf_text_chunk},
                ],
                temperature=0.1,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"},
            )
            latency_ms = int((perf_counter() - started_at) * 1000)
            record_llm_usage(
                user_id=user_id,
                operation="document_chunk_generation",
                model=model,
                response=output,
                latency_ms=latency_ms,
                document_processing_job_id=document_processing_job_id,
            )
            if not output.choices[0].message.content:
                raise Exception("No facts generated.")
            facts = GeneratedDocumentInformationChunks.model_validate_json(output.choices[0].message.content).facts
            print(f"Generated {len(facts)} facts for pdf text chunk {index}.")
            return facts
        except Exception as e:
            total_retries += 1
            if total_retries > 5:
                raise e
            retry_delay = get_retry_delay(e)
            await sleep(retry_delay)
            print(f"Failed to generate facts for pdf text chunk {index} with this err: {e}. Retrying in {retry_delay}s...")


async def get_matching_tags(
    user_id: int,
    pdf_text: str,
    document_processing_job_id: Optional[int] = None,
):
    tags_result = list(Tags.select().where(Tags.user_id == user_id))
    tags = [tag.name.lower() for tag in tags_result]
    if not tags:
        return []

    total_retries = 0
    while True:
        try:
            model = "llama-3.3-70b-versatile"
            started_at = perf_counter()
            output = await openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": GET_MATCHING_TAGS_SYSTEM_PROMPT.replace("{{tags_to_match_with}}", str(tags)),
                    },
                    {"role": "user", "content": pdf_text},
                ],
                temperature=0.1,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"},
            )
            latency_ms = int((perf_counter() - started_at) * 1000)
            record_llm_usage(
                user_id=user_id,
                operation="document_tag_matching",
                model=model,
                response=output,
                latency_ms=latency_ms,
                document_processing_job_id=document_processing_job_id,
            )
            if not output.choices[0].message.content:
                raise Exception("Empty response for generating matching tags.")
            matching_tag_names = GeneratedMatchingTags.model_validate_json(output.choices[0].message.content).tags
            matching_tag_ids: list[int] = []
            for tag_name in matching_tag_names:
                matching_tag = find(lambda tag: tag.name.lower() == tag_name.lower(), tags_result)
                if matching_tag:
                    matching_tag_ids.append(matching_tag.id)
            print(f"Generated matching tags {str(matching_tag_names)} for pdf text.")
            return matching_tag_ids
        except Exception as e:
            total_retries += 1
            if total_retries > 5:
                raise e
            retry_delay = get_retry_delay(e)
            await sleep(retry_delay)
            print(f"Failed to generate matching tags for pdf with this err: {e}. Retrying in {retry_delay}s...")


async def process_pdf_text(
    user_id: int,
    pdf_text_chunks: list[str],
    pdf_text: str,
    progress_callback: Callable[[int, str], None],
    document_processing_job_id: Optional[int] = None,
):
    document_information_chunks_from_each_pdf_text_chunk = []
    total_chunks = max(len(pdf_text_chunks), 1)
    for index, pdf_text_chunk in enumerate(pdf_text_chunks):
        progress_callback(15 + int((index / total_chunks) * 55), f"Generating facts {index + 1}/{total_chunks}")
        document_information_chunks_from_each_pdf_text_chunk.append(
            await generate_chunks(user_id, index, pdf_text_chunk, document_processing_job_id)
        )

    progress_callback(75, "Matching tags")
    matching_tag_ids = await get_matching_tags(user_id, pdf_text[0:5000], document_processing_job_id)
    return document_information_chunks_from_each_pdf_text_chunk, matching_tag_ids


def upload_document_sync(
    user_id: int,
    name: str,
    pdf_file: bytes,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    document_processing_job_id: Optional[int] = None,
):
    initialize_database(require_vector=True)
    progress_callback = progress_callback or (lambda progress, message: None)
    progress_callback(5, "Parsing PDF")
    parsed_pdf = pdftotext.PDF(BytesIO(pdf_file))
    pdf_text = "\n\n".join(parsed_pdf)
    pdf_text_chunks = [
        pdf_text[i : i + IDEAL_CHUNK_LENGTH]
        for i in range(0, len(pdf_text), IDEAL_CHUNK_LENGTH)
    ]

    progress_callback(10, f"Prepared {len(pdf_text_chunks)} text chunks")
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    try:
        document_information_chunks_from_each_pdf_text_chunk, matching_tag_ids = event_loop.run_until_complete(
            process_pdf_text(user_id, pdf_text_chunks, pdf_text, progress_callback, document_processing_job_id)
        )
    finally:
        event_loop.close()

    document_information_chunks = [
        chunk
        for chunks in document_information_chunks_from_each_pdf_text_chunk
        for chunk in chunks
    ]

    progress_callback(85, "Saving document")
    with db.atomic() as transaction:
        document_id = Documents.insert(name=name, user_id=user_id).execute()
        if document_information_chunks:
            DocumentInformationChunks.insert_many(
                [
                    {
                        "document_id": document_id,
                        "chunk": chunk,
                        "embedding": get_embedding(chunk),
                    }
                    for chunk in document_information_chunks
                ]
            ).execute()
        if matching_tag_ids:
            DocumentTags.insert_many(
                [
                    {"document_id": document_id, "tag_id": tag_id}
                    for tag_id in matching_tag_ids
                ]
            ).execute()
        transaction.commit()

    progress_callback(100, "Completed")
    print(
        f"Inserted {len(document_information_chunks)} facts for pdf {name} "
        f"with document id {document_id} and {len(matching_tag_ids)} matching tags."
    )
    return document_id
