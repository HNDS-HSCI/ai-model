import requests
import json

base_url = 'http://127.0.0.1:8000/process'
test_cases = [
    ('Math/Finance', 'If I have 5000 and invest 20% with a 5% tax, what is the final amount?'),
    ('Code/Synthesis', 'Write code for a salary calculator'),
    ('General/Social', 'Hello, who are you?'),
    ('Physics/Reduction', 'velocity is 30, time is 4, find distance')
]

for label, stimulus in test_cases:
    print(f'\n--- TESTING: {label} ---')
    print(f'Input: "{stimulus}"')
    try:
        r = requests.post(base_url, json={'stimulus': stimulus}, timeout=30)
        data = r.json()
        print(f'Success: {data.get("success")}')
        print(f'Confidence: {data.get("confidence")}')
        print(f'Concepts: {data.get("concepts_used")}')
        print(f'Response Snippet: {data.get("solution")[:200]}...')
    except Exception as e:
        print(f'Error: {e}')
