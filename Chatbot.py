import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import requests
import json
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROCESSED_DATA_DIR = "processed_data"
MODEL_NAME = "all-MiniLM-L6-v2"
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
OPENROUTER_MODEL = "deepseek/deepseek-r1-0528-qwen3-8b:free"
RELEVANCE_SIM_THRESHOLD = 0.35  # cosine similarity threshold to accept context

# Initialize embeddings model
embeddings_model = SentenceTransformer(MODEL_NAME)

class ProductData:
    def __init__(self, product_name: str):
        self.product_name = product_name
        self.data_dir = os.path.join(PROCESSED_DATA_DIR, product_name)
        self.faiss_index = None
        self.chunks = None
        self.embeddings = None
        self.load_data()

    def load_data(self):
        try:
            faiss_path = os.path.join(self.data_dir, "faiss_store", "index.faiss")
            if os.path.exists(faiss_path):
                self.faiss_index = faiss.read_index(faiss_path)
            chunks_path = os.path.join(self.data_dir, "chunks.pkl")
            if os.path.exists(chunks_path):
                with open(chunks_path, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                    self.embeddings = data['embeddings']
        except Exception as e:
            logger.error(f"Error loading data for {self.product_name}: {str(e)}")

class SimpleChatManager:
    def __init__(self):
        self.product_data = {}
        self.initialize_products()

    def initialize_products(self):
        try:
            if os.path.exists(PROCESSED_DATA_DIR):
                for product_name in os.listdir(PROCESSED_DATA_DIR):
                    product_path = os.path.join(PROCESSED_DATA_DIR, product_name)
                    if os.path.isdir(product_path):
                        self.product_data[product_name] = ProductData(product_name)
                        logger.info(f"Initialized data for product: {product_name}")
        except Exception as e:
            logger.error(f"Error initializing products: {str(e)}")
            raise

    def search_similar_chunks(self, query: str, product: str, k: int = 3) -> list:
        if product not in self.product_data:
            logger.warning(f"Product {product} not found in product data")
            return []
        product_data = self.product_data[product]
        if not product_data.faiss_index or not product_data.chunks:
            logger.warning(f"No FAISS index or chunks found for product {product}")
            return []
        try:
            query_embedding = embeddings_model.encode([query])[0]
            distances, indices = product_data.faiss_index.search(
                query_embedding.reshape(1, -1).astype('float32'), k
            )
            # Compute cosine similarities for top-k to enforce relevance
            # Use stored embeddings for robust similarity check
            query_norm = np.linalg.norm(query_embedding) + 1e-12
            relevant_chunks = []
            for rank, idx in enumerate(indices[0]):
                if idx < len(product_data.chunks):
                    chunk_embedding = product_data.embeddings[idx]
                    sim = float(np.dot(query_embedding, chunk_embedding) / ((np.linalg.norm(chunk_embedding) + 1e-12) * query_norm))
                    if sim >= RELEVANCE_SIM_THRESHOLD:
                        chunk = product_data.chunks[idx]
                        relevant_chunks.append(f"[{product.upper()}] {chunk}")
            if not relevant_chunks:
                logger.info(f"No relevant chunks found for product {product}")
                return []
            return relevant_chunks
        except Exception as e:
            logger.error(f"Error searching chunks for product {product}: {str(e)}")
            return []

    def generate_response(self, query: str, context: list, product: str) -> str:
        if not context:
            return (
                "Welcome to AllOfTech! We're a technology agency specializing in AI/ML, blockchain, web and mobile apps, UX/UI design, and branding. How can we help you achieve your goals?"
            )

        prompt = f"""Context:\n{chr(10).join(context)}\n\nInstructions:\n
        You are the voice of AllOfTech, a cutting-edge technology agency dedicated to delivering innovative solutions in AI/ML, blockchain, web development, mobile apps, UX/UI design, and graphics & branding. Your responses should reflect our commitment to empowering businesses with tailored, scalable, and secure digital ecosystems.

        Core Behavior:
        - Use a professional, approachable, and customer-focused tone.
        - Be clear, concise, and eager to assist with actionable insights.
        - Highlight AllOfTech's expertise in technology and design when relevant.
        - Avoid overly technical jargon unless the query demands it, ensuring responses are accessible to all clients.

        Grounding Rules (STRICT):
        - Only use factual information that appears in the Context above. Do NOT invent or assume details that are not present in the Context.
        - If the answer is not supported by the Context, say: "I don’t have that information in my current context." and suggest contacting us at contact.alloftech@gmail.com for confirmation.
        - For payment questions: mention ONLY the methods explicitly present in the Context. Do NOT add new payment methods (e.g., PayPal) unless they appear in the Context.
        - Keep answers concise and directly address the user's question.

        Respond to: "{query}"
        """

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                })
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenRouter API error: {response.text}")
                return "Sorry, I faced an issue while generating the response."
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "System interruption detected. Please try again shortly."

# Initialize the simple chat manager
simple_chat_manager = SimpleChatManager()

def chatbot(message: str, product: str = "AllOfTech") -> str:
    """
    Chatbot function that takes a message and product name, and returns the chatbot's response.
    """
    relevant_chunks = simple_chat_manager.search_similar_chunks(message, product)
    response = simple_chat_manager.generate_response(message, relevant_chunks, product)
    return response
