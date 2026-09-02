## Industrial visit at International Business Machines Coorporation(IBM) Research
IBM research located in Langata at CUAE, is one of IBM research centres in AFRiCA. The role of the research centre is to advance technology through AI and quantum computing that eventually shapes IBM products in the enteprise market.
It deals entirely with data processing, mainframes, databases, enteprise software, cloud, AI, hybrid cloud and quantum computing.
My main area of interest during the visit was hoe the fundamentals of AI learnt in class are brought into real world application.
## AI integration in IBM.
The AI here is an enteprise AI: it supports RAG development and enterprise knowledge grounding among other AI capabilities. the workflow involves:
Data-> Model->  Application ->Deployment -> Evaluation/monitoring -> Governance. 
### IBM Granite Model
Introduction to IBM granite model.Granite is IBM's family of open, enterprise-oriented AI models, covering multiple modalities, tasks and domains.Some are task oriented and some are domain oriented.
Granite ecosystem includes:
                    IBM GRANITE
                         │
       ┌─────────────────┼─────────────────┐
       ↓                 ↓                 ↓
    Language            Code             Vision
       │                 │                 │
       ↓                 ↓                 ↓
    Granite 4       Granite Code      Granite Vision
       
       ┌─────────────────┼─────────────────┐
       ↓                 ↓                 ↓
   Embeddings       Time Series        Safety/Guardians


The lesson from this is that modern AI engineering is not all about training a gigantic model from scratch, instead, select an appropriate foundation model, evaluate it, customize it and connect it to the enteprise data,add the agents, deploy. this optimizes cost and perfomance.
              Enterprise AI Application
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
        RAG Pipeline          Foundation Model
             │                   │
      ┌──────┴──────┐       ┌────┴─────┐
      ↓             ↓       ↓          ↓
  Embedding     Retrieval  Granite   OpenAI
      │             │
      └──────┬──────┘
             ↓
       Retrieved Context
             │
             ↓
       Selected LLM
             │
             ↓
          Answer
Regarding the choice of what to use between Granite model and OpenAI is determined by the security and data privacy of the data being fed to the LLM. Since it uses enterprise data measures should be put in place to avoid leaking through AI model. Due to this AI governance is really important here.
### RAG at IBM
The pipeline is as follows:
Document parsing → chunking → embedding → indexing → retrieval → reranking → context construction → LLM
At IBM granite embedding and also slate is employed. An important lesson is that the best embedding model gives you the best RAG.
### IBM Bob
This is the AI coding agent that helps the organization to tackle large global challenges and solutions. 
At this point we undestood what the meaning of AI fluency as a job requirement means. It was explained that you can be a good developer that can code line by line, but working with AI saves time. Therefore for effecient working with such an agent, we should move from pure prompt engineering to context engineering and from impressive demos to reliable production. Also the aspect of human in loop remains important because at times AI can make mistakes and for such a company one small mistake could cost millions of looses and lose of credebility therefore working with agents also requires understanding. And above all AI is not taking the place for developers but it is making developers work easier.
