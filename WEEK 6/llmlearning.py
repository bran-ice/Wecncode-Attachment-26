
Open In Colab

!pip install google-genai
     
Requirement already satisfied: google-genai in /usr/local/lib/python3.12/dist-packages (2.11.0)
Requirement already satisfied: anyio<5.0.0,>=4.8.0 in /usr/local/lib/python3.12/dist-packages (from google-genai) (4.14.2)
Requirement already satisfied: google-auth<3.0.0,>=2.48.1 in /usr/local/lib/python3.12/dist-packages (from google-auth[requests]<3.0.0,>=2.48.1->google-genai) (2.49.0)
Requirement already satisfied: httpx<1.0.0,>=0.28.1 in /usr/local/lib/python3.12/dist-packages (from google-genai) (0.28.1)
Requirement already satisfied: pydantic<3.0.0,>=2.12.5 in /usr/local/lib/python3.12/dist-packages (from google-genai) (2.13.4)
Requirement already satisfied: requests<3.0.0,>=2.28.1 in /usr/local/lib/python3.12/dist-packages (from google-genai) (2.32.4)
Requirement already satisfied: tenacity<9.2.0,>=8.2.3 in /usr/local/lib/python3.12/dist-packages (from google-genai) (9.1.4)
Requirement already satisfied: websockets<17.0,>=13.0.0 in /usr/local/lib/python3.12/dist-packages (from google-genai) (15.0.1)
Requirement already satisfied: typing-extensions<5.0.0,>=4.14.0 in /usr/local/lib/python3.12/dist-packages (from google-genai) (4.16.0)
Requirement already satisfied: distro<2,>=1.7.0 in /usr/local/lib/python3.12/dist-packages (from google-genai) (1.9.0)
Requirement already satisfied: sniffio in /usr/local/lib/python3.12/dist-packages (from google-genai) (1.3.1)
Requirement already satisfied: idna>=2.8 in /usr/local/lib/python3.12/dist-packages (from anyio<5.0.0,>=4.8.0->google-genai) (3.18)
Requirement already satisfied: pyasn1-modules>=0.2.1 in /usr/local/lib/python3.12/dist-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (0.4.2)
Requirement already satisfied: cryptography>=38.0.3 in /usr/local/lib/python3.12/dist-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (49.0.0)
Requirement already satisfied: rsa<5,>=3.1.4 in /usr/local/lib/python3.12/dist-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (4.9.1)
Requirement already satisfied: certifi in /usr/local/lib/python3.12/dist-packages (from httpx<1.0.0,>=0.28.1->google-genai) (2026.6.17)
Requirement already satisfied: httpcore==1.* in /usr/local/lib/python3.12/dist-packages (from httpx<1.0.0,>=0.28.1->google-genai) (1.0.9)
Requirement already satisfied: h11>=0.16 in /usr/local/lib/python3.12/dist-packages (from httpcore==1.*->httpx<1.0.0,>=0.28.1->google-genai) (0.16.0)
Requirement already satisfied: annotated-types>=0.6.0 in /usr/local/lib/python3.12/dist-packages (from pydantic<3.0.0,>=2.12.5->google-genai) (0.7.0)
Requirement already satisfied: pydantic-core==2.46.4 in /usr/local/lib/python3.12/dist-packages (from pydantic<3.0.0,>=2.12.5->google-genai) (2.46.4)
Requirement already satisfied: typing-inspection>=0.4.2 in /usr/local/lib/python3.12/dist-packages (from pydantic<3.0.0,>=2.12.5->google-genai) (0.4.2)
Requirement already satisfied: charset_normalizer<4,>=2 in /usr/local/lib/python3.12/dist-packages (from requests<3.0.0,>=2.28.1->google-genai) (3.4.9)
Requirement already satisfied: urllib3<3,>=1.21.1 in /usr/local/lib/python3.12/dist-packages (from requests<3.0.0,>=2.28.1->google-genai) (2.5.0)
Requirement already satisfied: cffi>=2.0.0 in /usr/local/lib/python3.12/dist-packages (from cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (2.1.0)
Requirement already satisfied: pyasn1<0.7.0,>=0.6.1 in /usr/local/lib/python3.12/dist-packages (from pyasn1-modules>=0.2.1->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (0.6.4)
Requirement already satisfied: pycparser in /usr/local/lib/python3.12/dist-packages (from cffi>=2.0.0->cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai) (3.0)

from google import genai
from google.colab import userdata
     

api_key = userdata.get('llmbasics-api-key')
client = genai.Client(api_key=api_key)
print("Setup complete! The Gemini client is ready.")
     
Setup complete! The Gemini client is ready.

text_to_analyze = """
"I can still see the boy, about ten years old, sitting in the row ahead of me in a subway car, his face frozen in a mask of sullen terror, his eyes wide with a frantic panic. He was wedged between two larger boys who were bullying him, taunting him with a cruel rhythm,
 jabbing him in the ribs, knocking his books to the floor."
"""
# We can count tokens without actually making a paid generation request
response = client.models.count_tokens(
    model='gemini-2.5-flash',
    contents=text_to_analyze,
)
print(f"The text above contains {len(text_to_analyze.split())} words.")
print(f"The model sees it as {response.total_tokens} tokens.")
     
The text above contains 65 words.
The model sees it as 82 tokens.

# Pricing for Gemini 2.5 Flash (per 1 million tokens)
FLASH_INPUT_COST = 0.075
FLASH_OUTPUT_COST = 0.30
def calculate_cost(input_tokens, output_tokens):
    # Divide by 1,000,000 to get the cost per million
    input_cost = (input_tokens / 1_000_000) * FLASH_INPUT_COST
    output_cost = (output_tokens / 1_000_000) * FLASH_OUTPUT_COST
    total_cost = input_cost + output_cost
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total": total_cost
    }
# Example: Processing a small book and getting a short summary
book_tokens = 65
summary_tokens = 82
costs = calculate_cost(book_tokens, summary_tokens)
print(f"Cost to read book: ${costs['input_cost']:.6f}")
print(f"Cost to write summary: ${costs['output_cost']:.6f}")
print(f"Total API Cost: ${costs['total']:.6f}")
     
Cost to read book: $0.000005
Cost to write summary: $0.000025
Total API Cost: $0.000029

prompt = "In Daniel Goleman's book Emotional Intelligence, explain why emotional intelligence matters more than IQ"

# Generate the response
response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents=prompt
)
print("MODEL RESPONSE:")
print(response.text)
print("-" * 40)
# Extract token usage from the response metadata
usage = response.usage_metadata
input_toks = usage.prompt_token_count
output_toks = usage.candidates_token_count
total_toks = usage.total_token_count
print("TOKEN USAGE RECEIPT:")
print(f"Prompt (Input) Tokens: {input_toks}")
print(f"Response (Output) Tokens: {output_toks}")
print(f"Total Tokens: {total_toks}")
# Calculate actual cost using our function
actual_cost = calculate_cost(input_toks, output_toks)
print(f"Total Cost for this API call: ${actual_cost['total']:.8f}")
     
MODEL RESPONSE:
In his groundbreaking 1995 book *Emotional Intelligence: Why It Can Matter More Than IQ*, psychologist and science journalist Daniel Goleman argues that traditional measure of intelligence (IQ) is a surprisingly poor predictor of life success, health, leadership, and personal happiness. 

While Goleman acknowledges that IQ is a great predictor of academic performance, he estimates that **IQ accounts for only about 20% of the factors that determine success in life**. The remaining 80% comes from other forces—dominated by **Emotional Intelligence (EQ)**.

Here is a breakdown of why Goleman argues EQ matters more than IQ:

---

### 1. The "Threshold" Principle vs. The Differentiator
Goleman argues that IQ acts merely as a "threshold capability." You need a certain level of IQ to get into college, pass professional exams, or get hired in a technical field. 
However, once you enter the workplace, **everyone around you has a similar IQ**. At that point, cognitive ability ceases to be the competitive advantage. What differentiates top performers, leaders, and successful individuals from the rest is their EQ—how they manage themselves, deal with stress, collaborate, and navigate social dynamics.

### 2. Brain Design and the "Amygdala Hijack"
Goleman uses neuroscience to explain why high IQ can be rendered useless by low EQ. The human brain evolved so that incoming sensory information passes through the emotional center of the brain (the limbic system/amygdala) before reaching the rational brain (the prefrontal cortex).

When a person lacks emotional self-regulation, a perceived threat or high stress triggers an **"amygdala hijack."** Emotional impulses override rational thought. 
* **The result:** A genius with a 150 IQ who lacks emotional control can throw a temper tantrum, freeze under pressure, or make disastrous impulsive decisions. Without EQ, your IQ is essentially held hostage by your emotions.

### 3. Real-World Application vs. Academic Ability
IQ measures abstract reasoning, linguistic ability, and spatial logic. These are crucial for solving math problems or taking standardized tests, but life rarely presents problems in a standardized test format.

EQ equips people to handle real-world complexities that IQ cannot solve:
* **Self-Awareness:** Recognizing your own emotions, strengths, and limits.
* **Self-Regulation:** Managing disruptive impulses, anxiety, and anger.
* **Motivation:** Pushing through failure and frustration (grit and resilience).
* **Empathy:** Understanding the emotions and perspectives of others.
* **Social Skills:** Building networks, resolving conflicts, and inspiring people.

A high-IQ individual who lacks empathy will struggle to lead a team, negotiate a contract, or maintain a healthy marriage.

### 4. Leadership and Organizational Success
In the business world, Goleman’s research showed that EQ is twice as important as technical skills and IQ combined for outstanding leadership performance. 
* **IQ gets you hired; EQ gets you promoted.** 
* Leaders with high EQ create psychologically safe environments, inspire loyalty, and manage organizational change effectively. High-IQ, low-EQ leaders often create toxic, high-stress environments that lead to burnout and high employee turnover.

### 5. Health and Well-Being
IQ has very little bearing on physical and mental health. Low EQ, on the other hand, often manifests as chronic stress, anxiety, and uncontrolled anger. 
Goleman highlights medical research showing that persistent negative emotions damage cardiovascular health, suppress the immune system, and increase vulnerability to disease. High EQ provides the coping mechanisms required to mitigate chronic stress, leading to longer, healthier lives.

### 6. IQ is Fixed; EQ is Malleable
One of Goleman's most vital arguments is practical: **IQ is largely genetic and remains relatively stable after childhood.** You cannot dramatically raise your baseline IQ as an adult.

**EQ, however, can be learned and developed at any age.** The neural pathways governing emotional responses are adaptable (neuroplasticity). Through self-reflection, feedback, and deliberate practice, individuals can improve their self-control, empathy, and social skills throughout their lives. 

---

### Summary
Daniel Goleman does not argue that IQ is useless. Rather, he asserts that **IQ gets your foot in the door, but EQ determines how far you go once you're inside.** 

A high IQ might make you a brilliant thinker, but high EQ enables you to thrive as a leader, friend, partner, and resilient human being navigating a complex, emotionally driven world.
----------------------------------------
TOKEN USAGE RECEIPT:
Prompt (Input) Tokens: 20
Response (Output) Tokens: 958
Total Tokens: 2020
Total Cost for this API call: $0.00028890

# Pricing for GPT-40-mini (per 1 million tokens)
FLASH_INPUT_COST = 0.15
FLASH_OUTPUT_COST = 0.6
def calculate_cost(input_tokens, output_tokens):
    # Divide by 1,000,000 to get the cost per million
    input_cost = (input_tokens / 1_000_000) * FLASH_INPUT_COST
    output_cost = (output_tokens / 1_000_000) * FLASH_OUTPUT_COST
    total_cost = input_cost + output_cost
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total": total_cost
    }
# Example: Processing a small book and getting a short summary
book_tokens = 65
summary_tokens = 82
costs = calculate_cost(book_tokens, summary_tokens)
print(f"Cost to read book: ${costs['input_cost']:.6f}")
print(f"Cost to write summary: ${costs['output_cost']:.6f}")
print(f"Total API Cost: ${costs['total']:.6f}")
     
Cost to read book: $0.000010
Cost to write summary: $0.000049
Total API Cost: $0.000059

# Pricing for claude sonnet 5 (per 1 million tokens)
INPUT_COST = 2
OUTPUT_COST = 15
def calculate_cost(input_tokens, output_tokens):
    # Divide by 1,000,000 to get the cost per million
    input_cost = (input_tokens / 1_000_000) * INPUT_COST
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST
    total_cost = input_cost + output_cost
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total": total_cost
    }
# Example: Processing a small book and getting a short summary
book_tokens = 65
summary_tokens = 82
costs = calculate_cost(book_tokens, summary_tokens)
print(f"Cost to read book: ${costs['input_cost']:.6f}")
print(f"Cost to write summary: ${costs['output_cost']:.6f}")
print(f"Total API Cost: ${costs['total']:.6f}")
     
Cost to read book: $0.000130
Cost to write summary: $0.001230
Total API Cost: $0.001360