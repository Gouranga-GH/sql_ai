# Gradio: For building the web UI
import gradio as gr
# Pandas: For handling tabular data (e.g., SQL query results)
import pandas as pd
# LangChain: For creating the SQL agent that interprets natural language
from langchain.agents import create_sql_agent
# LangChain SQLDatabase: For database abstraction and connection
from langchain.sql_database import SQLDatabase
# LangChain AgentType: For specifying the type of agent to use
from langchain.agents.agent_types import AgentType
# LangChain Groq: For integrating with Groq's LLM (Llama3-8b-8192)
from langchain_groq import ChatGroq
# SQLAlchemy: For creating database engine and connections
from sqlalchemy import create_engine
# re: Regular expressions, used for string processing (if needed)
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
    # Ensure all required fields are provided
    if not all([mysql_host, mysql_user, mysql_password, mysql_db, api_key]):
        return None, None
    try:
        # Build the database URI for SQLAlchemy
        db_uri = f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
        # Create a SQLDatabase object (LangChain abstraction over SQLAlchemy engine)
        db = SQLDatabase(create_engine(db_uri))
        # Initialize the Groq LLM (Llama3-8b-8192) with the provided API key
        llm = ChatGroq(
            groq_api_key=api_key,
            model_name="Llama3-8b-8192",
            streaming=False
        )
        # Create the LangChain SQL agent for natural language to SQL translation
        agent = create_sql_agent(
            llm=llm,
            db=db,
            verbose=False,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
        return db, agent
    except Exception as e:
        # If any error occurs (e.g., bad credentials), return None
        return None, None

# Function to test database connection

def test_connection(mysql_host, mysql_user, mysql_password, mysql_db):
    """
    Attempts to connect to the MySQL database using SQLAlchemy.
    Returns (True, message) if successful, else (False, error message).
    """
    try:
        # Create a SQLAlchemy engine and attempt to connect
        engine = create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}")
        with engine.connect() as conn:
            return True, "Connection successful!"
    except Exception as e:
        # Return error message if connection fails
        return False, f"Connection failed: {str(e)}"

# Main chat logic

def chat_with_db(history, user_query, mysql_host, mysql_user, mysql_password, mysql_db, api_key):
    """
    Handles a user query, interacts with the SQL agent, and returns updated chat history.
    """
    # Set up the database and agent
    db, agent = setup_database_agent(mysql_host, mysql_user, mysql_password, mysql_db, api_key)
    if not db or not agent:
        # If setup fails, notify the user in chat
        history.append((user_query, "\u274c Database or API key not configured properly."))
        return history

    # Add user message to chat history
    history.append((user_query, None))
    try:
        # Get response from agent (natural language to SQL to result)
        response = agent.run(user_query)
        # Add assistant response to chat history
        history[-1] = (user_query, response)
        return history
    except Exception as e:
        # If an error occurs during query execution, show error in chat
        history[-1] = (user_query, f"\u274c Error: {str(e)}")
        return history

# Gradio UI definition

def main():
    # Create the Gradio Blocks UI
    with gr.Blocks(title="SQL AI Explorer") as demo:
        # App title and description
        gr.Markdown("""
        # \ud83d\uddc4\ufe0f SQL AI Explorer
        **Ask your database anything in plain English!**
        """)
        # Configuration section for DB and API credentials
        with gr.Accordion("Configuration", open=True):
            with gr.Row():
                # MySQL connection fields
                mysql_host = gr.Textbox(label="MySQL Host", placeholder="localhost", value="localhost")
                mysql_user = gr.Textbox(label="MySQL User", placeholder="root", value="root")
                mysql_password = gr.Textbox(label="MySQL Password", type="password")
                mysql_db = gr.Textbox(label="MySQL Database", placeholder="your_database")
                # Groq API key field
                api_key = gr.Textbox(label="Groq API Key", type="password")
            # Button to test DB connection
            test_btn = gr.Button("Test Connection")
            # Output area for connection test result
            test_output = gr.Markdown()
            # Handler for test connection button
            def on_test_click(host, user, pwd, db,):
                ok, msg = test_connection(host, user, pwd, db)
                return msg
            test_btn.click(on_test_click, [mysql_host, mysql_user, mysql_password, mysql_db], test_output)
        gr.Markdown("---")
        # Chatbot UI for conversation
        chatbot = gr.Chatbot(label="SQL AI Chat", height=400)
        with gr.Row():
            # User input textbox and send button
            user_input = gr.Textbox(label="Ask your database anything...", placeholder="e.g., Show me all users with age > 25", scale=4)
            send_btn = gr.Button("Send", scale=1)
        # Button to clear chat history
        clear_btn = gr.Button("Clear Chat")

        # State for chat history (persists across interactions)
        state = gr.State([])

        # Handler for sending a user query
        def on_send(user_query, history, host, user, pwd, db, key):
            # Ignore empty queries
            if not user_query.strip():
                return history
            # Process the query and update chat history
            history = chat_with_db(history, user_query, host, user, pwd, db, key)
            return history

        # Connect send button to handler
        send_btn.click(
            on_send,
            [user_input, state, mysql_host, mysql_user, mysql_password, mysql_db, api_key],
            chatbot,
            show_progress=True
        )
        # Allow pressing Enter in textbox to send
        user_input.submit(
            on_send,
            [user_input, state, mysql_host, mysql_user, mysql_password, mysql_db, api_key],
            chatbot,
            show_progress=True
        )
        # Clear chat button resets the chat window
        clear_btn.click(lambda: [], None, chatbot)

        # Footer with credits
        gr.Markdown("""
        ---
        <div style=\"text-align: center; color: #666; padding: 1rem;\">
            <p>Powered by LangChain + Groq + Gradio</p>
            <p>\u2728 Ask anything, get answers in style \u2728</p>
        </div>
        """, elem_id="footer")
    # Launch the Gradio app
    demo.launch()

# Entry point: run the app if this script is executed directly
if __name__ == "__main__":
    main() 