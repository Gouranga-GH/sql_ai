import gradio as gr
import pandas as pd
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain_groq import ChatGroq
from sqlalchemy import create_engine
import re

# -----------------------------
# SQL AI Explorer (Gradio App)
# -----------------------------
# This app allows users to connect to a MySQL database and interact with it using natural language queries powered by LangChain and Groq LLM.
# The app provides a chat interface.
#
# The app is designed for deployment on Hugging Face Spaces (Gradio standard).
# -----------------------------

# Helper function to set up the database and agent

def setup_database_agent(mysql_host, mysql_user, mysql_password, mysql_db, api_key):
    """
    Establishes a connection to the MySQL database and sets up the LangChain SQL agent.
    Returns (db, agent) if successful, else (None, None).
    """
    if not all([mysql_host, mysql_user, mysql_password, mysql_db, api_key]):
        return None, None
    try:
        db_uri = f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
        db = SQLDatabase(create_engine(db_uri))
        llm = ChatGroq(
            groq_api_key=api_key,
            model_name="Llama3-8b-8192",
            streaming=False
        )
        agent = create_sql_agent(
            llm=llm,
            db=db,
            verbose=False,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
        return db, agent
    except Exception as e:
        return None, None

# Function to test database connection

def test_connection(mysql_host, mysql_user, mysql_password, mysql_db):
    try:
        engine = create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}")
        with engine.connect() as conn:
            return True, "Connection successful!"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

# Main chat logic

def chat_with_db(history, user_query, mysql_host, mysql_user, mysql_password, mysql_db, api_key):
    """
    Handles a user query, interacts with the SQL agent, and returns updated chat history.
    """
    db, agent = setup_database_agent(mysql_host, mysql_user, mysql_password, mysql_db, api_key)
    if not db or not agent:
        history.append((user_query, "❌ Database or API key not configured properly."))
        return history

    # Add user message
    history.append((user_query, None))
    try:
        # Get response from agent
        response = agent.run(user_query)
        # Add assistant response
        history[-1] = (user_query, response)
        return history
    except Exception as e:
        history[-1] = (user_query, f"❌ Error: {str(e)}")
        return history

# Gradio UI definition

def main():
    with gr.Blocks(title="SQL AI Explorer") as demo:
        gr.Markdown("""
        # 🗄️ SQL AI Explorer
        **Ask your database anything in plain English!**
        """)
        with gr.Accordion("Configuration", open=True):
            with gr.Row():
                mysql_host = gr.Textbox(label="MySQL Host", placeholder="localhost", value="localhost")
                mysql_user = gr.Textbox(label="MySQL User", placeholder="root", value="root")
                mysql_password = gr.Textbox(label="MySQL Password", type="password")
                mysql_db = gr.Textbox(label="MySQL Database", placeholder="your_database")
                api_key = gr.Textbox(label="Groq API Key", type="password")
            test_btn = gr.Button("Test Connection")
            test_output = gr.Markdown()
            def on_test_click(host, user, pwd, db,):
                ok, msg = test_connection(host, user, pwd, db)
                return msg
            test_btn.click(on_test_click, [mysql_host, mysql_user, mysql_password, mysql_db], test_output)
        gr.Markdown("---")
        chatbot = gr.Chatbot(label="SQL AI Chat", height=400)
        with gr.Row():
            user_input = gr.Textbox(label="Ask your database anything...", placeholder="e.g., Show me all users with age > 25", scale=4)
            send_btn = gr.Button("Send", scale=1)
        clear_btn = gr.Button("Clear Chat")

        # State for chat history
        state = gr.State([])

        def on_send(user_query, history, host, user, pwd, db, key):
            if not user_query.strip():
                return history
            history = chat_with_db(history, user_query, host, user, pwd, db, key)
            return history

        send_btn.click(
            on_send,
            [user_input, state, mysql_host, mysql_user, mysql_password, mysql_db, api_key],
            chatbot,
            show_progress=True
        )
        user_input.submit(
            on_send,
            [user_input, state, mysql_host, mysql_user, mysql_password, mysql_db, api_key],
            chatbot,
            show_progress=True
        )
        clear_btn.click(lambda: [], None, chatbot)

        gr.Markdown("""
        ---
        <div style="text-align: center; color: #666; padding: 1rem;">
            <p>Powered by LangChain + Groq + Gradio</p>
            <p>✨ Ask anything, get answers in style ✨</p>
        </div>
        """, elem_id="footer")
    demo.launch()

if __name__ == "__main__":
    main() 