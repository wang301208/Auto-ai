# Auto-GPT

Auto-GPT is an autonomous GPT-4 experiment that chains thoughts to accomplish goals. Key capabilities include:

* 🌐 Internet search and information gathering
* 💾 Memory and workspace file management
* 🔌 Plugin system with gap detection
* 🔁 [Self Improvement Loop](self_improvement.md) for automatic self-development
* 🧬 [AlphaEvolve strategy evolution](evolve_population.md) to iterate on agent behaviors

Please follow the [Installation](/setup/) guide to get started.

NOTE: It is recommended to use a virtual machine/container (docker) for tasks that require high security measures to prevent any potential harm to the main computer's system and data. If you are considering to use Auto-GPT outside a virtualized/containerized environment, you are *strongly* advised to use a separate user account just for running Auto-GPT. This is even more important if you are going to allow Auto-GPT to write/execute scripts and run shell commands!

It is for these reasons that executing python scripts is explicitly disabled when running outside a container environment.
