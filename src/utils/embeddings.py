import numpy as np
from openai import OpenAI
from openai import APIError
import asyncio

from ..utils.cache import json_cache

client = OpenAI()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    similarity = dot_product / (norm_a * norm_b)
    return similarity

async def get_embedding(text: str, model="text-embedding-ada-002", max_retries=3) -> np.ndarray:
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.embeddings.create,
                input=[text.replace("\n", " ")],
                model=model
            )

            embedding = response.data[0].embedding

            return np.array(embedding)
        except APIError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                raise e  # If all retries failed, raise the exception
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                raise e  # If all retries failed, raise the exception
