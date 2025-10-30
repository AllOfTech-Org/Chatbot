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
        # Return ALL chunks for the product to ensure full info is provided
        return [f"[{product.upper()}] {chunk}" for chunk in product_data.chunks]

    def generate_response(self, query: str, context: list, product: str) -> str:
        # If context exists, return the full product info directly (all chunks combined)
        if context:
            return "\n\n".join(context)
        # Fallback welcome if no context/data is available
        return "Welcome to AllOfTech! We're a technology agency specializing in AI/ML, blockchain, web and mobile apps, UX/UI design, and branding. How can we help you achieve your goals?"

# Initialize the simple chat manager
simple_chat_manager = SimpleChatManager()

def chatbot(message: str, product: str = "AllOfTech") -> str:
    """
    Chatbot function that takes a message and product name, and returns the chatbot's response.
    """
    relevant_chunks = simple_chat_manager.search_similar_chunks(message, product)
    response = simple_chat_manager.generate_response(message, relevant_chunks, product)
    return response
