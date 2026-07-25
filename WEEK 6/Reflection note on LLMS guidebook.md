# LLMS, APIs AND TOKENS GUIDEBOOK REFLECTION
## Tokens
LLMS do not process the text letter by letter or word by word, they process the texts in chunks called tokens.
Token is a sequence that a model has learnt to treat as a single semantic unit.The words are converted into tokaens by a tokenizer. for english words one tocken is equal to three quaters of the word.Tokenization improves efficiency processing and vocubulary size. It allows the model to handle the unseen words by breaking them into subcomponents. It reduces the memory usage unlike word by word processing or character by character processing which requires large computational.
## Visualizing slicing
The texts are givens IDs. Capital letters have different IDs from lowercases. the punctions are often a separate token. leading spaces are also includede in the tokens.
## Parsing process
This involves the Input which is the entered prompt text, Encoding which involes scanning the document against pretrained vocabularies, Integer translation involves converting tokens into unique ids from text, Model processing involves operation of the integer id to determine or predict the next id. finally Decoding which involves now translating back into human readable language.
## API cost and calculation.
Consumption is measured in terms of the tokens. The tockens are classified into Prompt tokens(inputs) and completion token(output).
## Context window
This is the maximum number of tokens the model can hold in memory during a single API call. Statelessness is the condition of LLMs where they do not remember the previous interactions hence one must append the entire chat history into new prompt hence leading to a linear growth in tokens
