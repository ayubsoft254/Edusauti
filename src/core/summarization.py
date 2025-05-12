import os
from .azure_clients import get_openai_client

async def generate_summary(text):
    """Generate educational summary using Azure OpenAI"""
    openai_client = get_openai_client()
    
    prompt = f"""
    As an educational AI, your task is to create a teacher-like summary of the following text.
    Focus on key educational concepts, organize the content in a clear, structured way,
    and ensure it's easy to follow.
    
    Text to summarize:
    {text}
    
    Create an educational summary that:
    1. Highlights the main concepts
    2. Explains complex ideas in simple terms
    3. Follows a logical structure with clear sections
    4. Uses a teaching tone similar to a classroom lecture
    """
    
    response = openai_client.Completion.create(
        engine=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        prompt=prompt,
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].text.strip()