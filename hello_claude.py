import anthropic

client = anthropic.Anthropic()  # finds your API key automatically

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "Say hello and tell me you're ready to help edit a magazine."}
    ]
)

print(message.content[0].text)