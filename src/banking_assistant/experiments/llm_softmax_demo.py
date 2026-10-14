import math


def softmax(logits: list[float]) -> list[float]:
    maximum = max(logits)

    exponentials = [math.exp(logit - maximum) for logit in logits]

    total = sum(exponentials)

    return [value / total for value in exponentials]


tokens = ["A", "Savings", "The"]
logits = [3.0, 2.0, 1.0]

probabilities = softmax(logits)

for token, probability in zip(tokens, probabilities):
    print(f"{token}: {probability:.2%}")
