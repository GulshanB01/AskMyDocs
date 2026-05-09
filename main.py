import streamlit as st
from frontend.auth import get_current_user, render_login_page, render_sidebar_user

st.set_page_config(page_title="AskMyDocs")

current_user = get_current_user()

if not current_user:
    render_login_page()
    st.stop()

render_sidebar_user()

home_page = st.Page("app_pages/Chat_With_Documents.py", title="Chat With Documents")
manage_docs_page = st.Page("app_pages/Manage_Documents.py", title="Manage Documents")
manage_tags_page = st.Page("app_pages/Manage_Tags.py", title="Manage Tags")
admin_monitoring_page = st.Page("app_pages/Admin_Monitoring.py", title="Admin / Monitoring")

pages = [home_page, manage_docs_page, manage_tags_page]
if current_user.is_admin:
    pages.append(admin_monitoring_page)

pg = st.navigation(pages)
pg.run()
