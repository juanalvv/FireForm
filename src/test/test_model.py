# test_ollama.py
import ollama
import config

try:
    response = ollama.chat(model=config.OLLAMA_MODEL, messages=[
        {'role': 'user', 'content': 'Say hello in Spanish'}
    ])
    print("Success! Response:", response['message']['content'])
except Exception as e:
    print("Error:", e)
