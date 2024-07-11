<p align="center">
  <h1 align="center"> Co-designed Prompts in Collaborative LLM-based Agent to Agent simulation </h1>
  <p align="center">
     The original post explaning the solution
  <a href="https://blog.langchain.dev/gpteam-a-multi-agent-simulation/"><b>Blog Post</b></a>
  
  </p>
    <div align="center">
     <img src="https://github.com/anonette/GPTeam/assets/5162819/a4ae4a3b-83cb-4821-aa55-f84f5fee3530" alt="GitHub Image">
      </div>
</p>

## About GPTeam

GPTeam uses GPT-4 to create multiple agents who collaborate to achieve predefined goals. Their main objective ofwas to explore the potential of GPT models in enhancing multi-agent productivity and effective communication.
We appropriated the project to do research on deliberation over co-designing prompts and following the simulation in a group setting, comparing real and simulated discussions, or enacting the issues to experience catharsis in decision making.

Related papers:   
 Governance in Silico: Experimental Sandbox for Policymaking over AI Agents
[https://dl.designresearchsociety.org/drs-conference-papers/drs2024/researchpapers/11/](https://dl.designresearchsociety.org/drs-conference-papers/drs2024/researchpapers/11/) 

Sandboxes as “trading zones" for engaging with AI regulation, ethics, and the EU AI Act: How to Reclaim Agency over the Future?
[https://osf.io/preprints/socarxiv/59qna](https://osf.io/preprints/socarxiv/59qna) 


Video demo of the AI fable (appropriated the original use case): [https://www.youtube.com/watch?v=cIxhI1d6NsM](https://youtu.be/xIZlo0f8vic?t=2) 
Soon more... 

Read more about the architecture here: https://blog.langchain.dev/gpteam-a-multi-agent-simulation/

## Getting started
### Deps
 - install [VScode](https://code.visualstudio.com/Download) - while not a must, it helps.
 - install [python 3.10+](https://www.python.org/downloads/release/python-3124/) - scroll down and pick you OS
 - install [git](https://git-scm.com/downloads) 

If on **windows**, you will need to enable linux subsystem (WSL, here's [an how-to](https://learn.microsoft.com/en-us/windows/wsl/install))  
and then inside VSCode click the blue box[1] and choose WSL[2]

<img src="https://github.com/anonette/GPTeam/assets/222526/7ed1f2ee-a834-4bb2-acf0-c6819549ab7b" width="400">


### how to run
inside vscode, run the following in the terminal

Clone the project repository to your local machine  
`git clone https://github.com/anonette/GPTeam`

Move to the repository directory  
`cd gpteam`

Run `python setup.py` to check your environment setup and configure it as needed

Update the environment variables in `.env` with your API Keys. You will need an OpenAI API key, which you can obtain [here](https://platform.openai.com/account/api-keys). Supplying API keys for optional services will enable the use of other tools.

Launch the world by running 
`poetry run world`

To run the world cheaply, you can use `poetry run world --turbo`. This will use gpt3.5-turbo for all LLM calls which is a lot cheaper, but expect worse results!

Now you can observe the world in action and watch as the agents interact with each other, working together to accomplish their assigned directives.

## How it works

GPTeam employs separate agents, each equipped with a memory, that interact with one another using communication as a tool. The implementation of agent memory and reflection is inspired by [this research paper](https://arxiv.org/pdf/2304.03442.pdf). Agents move around the world and perform tasks in different locations, depending on what they are doing and where other agents are located. They can speak to eachother and collaborate on tasks, working in parallel towards common goals.

## Viewing Agents

The world is a busy place! To get a view of what different agents are doing whilst the world is running, you can visit the `agents/` folder where there is a txt file for each agent containing a summary of their current state.

## Changing the world

To change the world, all you need to do is:

1. Make changes to the `config.json` by updating the available agents or locations
2. Reset your database: `poetry run db-reset`
3. Run the world again: `poetry run world`

## Setting up the Discord Integration

Read through the dedicated [Discord setup docs](DISCORD.md)

## Using with Anthropic Claude

Make sure you have an `ANTHROPIC_API_KEY` in your env, then you can use `poetry run world --claude` which will run the world using `claude-v1` for some calls and `claude-v1-instant` for others.

## Using with Window

Make sure you have the [Window extension](https://windowai.io/) installed, then you can use `poetry run world --window`. Some models may be slow to respond, since the prompts are very long.

## Contributing

We enthusiastically welcome contributions to GPTeam! To contribute, please follow these steps:

1. Fork the project repository to your own account
2. Create a new branch for your changes
3. Implement your changes to the project code
4. Submit a pull request to the main project repository

We will review your pull request and provide feedback as necessary.

## License

Licensed under the [MIT license](LICENSE).
