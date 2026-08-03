# REFLECTION NOTE ON PYDANTIC MODEL AND APPLICATION IN REAL WORLD
## What is pydantic
Pydantic is a data validation library that acts as a bouncer for your code. It ensures that the data you receive (especially from unpredictable AI models) is exactly the type and format you expect.
What pydantic does basically is:
It enforces types: If the code expects an integer and it receives a string it catches it and throws an error.
It avoids the multiple if else statements to manually check the incoming data by using pythonic classes.
It guarantes structure ensuring that dictionaries or JSON objects contains all the fields you need before attempting to process them.
## Real World Use Case
A real world application of pydantic is in automated smart contract auditing at Web3 security firm for example by blockchain developers to inspect code and output a security report. LLMs are notorious of hallucinations, they may hallucinate to give a value to a key which initially was not provide or even miss out some fields. In the case of smart contract auditing if this happens if the AI generates the security report as a freefform the frontend will not be able to read it hence crushing.
By using pydantic, the developer provides the exact output schema that the AI must follow, pydantic forces the response into this exact structure. If there is any missing field and a default was not provided, the pydantic automatically catches it and throws an error for it to be corrected before anything is shown to the user.
## How Pydantic Documentation is done by Engineers.
This includes:
Defining the Schema and data types, this involves documenting the exact field requirement.
Establishing best practice for edge cases, documenting validation rules so that if information is missing from the source text, output is null rather than hallucination.
