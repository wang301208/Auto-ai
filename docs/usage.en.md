# Usage

## Command Line Arguments
Running with `--help` lists all the possible command line arguments you can pass:

```shell
agpt --help
```

!!! note
    Replace anything in angled brackets (<>) to a value you want to specify

Here are some common arguments you can use when running Auto-GPT:

* Run Auto-GPT with a different AI Settings file

```shell
agpt --ai-settings <filename>
```

* Run Auto-GPT with a different Prompt Settings file

```shell
agpt --prompt-settings <filename>
```

* Specify a memory backend

```shell
agpt --use-memory  <memory-backend>
```

!!! note
    There are shorthands for some of these flags, for example `-m` for `--use-memory`.  
    Use `agpt --help` for more information.

### Speak Mode

Enter this command to use TTS _(Text-to-Speech)_ for Auto-GPT

```shell
agpt --speak
```

### 💀 Continuous Mode ⚠️

Run the AI **without** user authorization, 100% automated.
Continuous mode is NOT recommended.
It is potentially dangerous and may cause your AI to run forever or carry out actions you would not usually authorize.
Use at your own risk.

```shell
agpt --continuous
```

To exit the program, press ++ctrl+c++

### ♻️ Self-Feedback Mode ⚠️

Running Self-Feedback will **INCREASE** token use and thus cost more. This feature enables the agent to provide self-feedback by verifying its own actions and checking if they align with its current goals. If not, it will provide better feedback for the next loop. To enable this feature for the current loop, input `S` into the input field.

### GPT-3.5 ONLY Mode

If you don't have access to GPT-4, this mode allows you to use Auto-GPT!

```shell
agpt --gpt3only
```

You can achieve the same by setting `SMART_LLM` in `.env` to `gpt-3.5-turbo`.

### GPT-4 ONLY Mode

If you have access to GPT-4, this mode allows you to use Auto-GPT solely with GPT-4.
This may give your bot increased intelligence.

```shell
agpt --gpt4only
```

!!! warning
    Since GPT-4 is more expensive to use, running Auto-GPT in GPT-4-only mode will
    increase your API costs.

## Logs

Activity, Error, and Debug logs are located in `./logs`

!!! tip 
    Do you notice weird behavior with your agent? Do you have an interesting use case? Do you have a bug you want to report?
    Follow the step below to enable your logs. You can include these logs when making an issue report or discussing an issue with us.

To print out debug logs:

```shell
agpt --debug
```

## Disabling Command Categories

If you want to selectively disable some command groups, you can use the `DISABLED_COMMAND_CATEGORIES` config in your `.env`. You can find the list of categories in your `.env.template`

For example, to disable coding related features, set it to the value below:

```ini
DISABLED_COMMAND_CATEGORIES=autogpt.commands.execute_code
```

## Running AlphaEvolve

To launch an AlphaEvolve workflow using the unified CLI:

```shell
agpt alphaevolve path/to/initial_program.py path/to/evaluator.py --config path/to/config.yaml
```

Run `agpt alphaevolve --help` to see all available options.
