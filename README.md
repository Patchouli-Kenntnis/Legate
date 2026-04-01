# Legate

This repository hosts an open-source coding and file management agent utilizing OpenAI's chat models. It is implemented as a command-line interface that processes user inputs and returns dynamic responses from the AI model.


## Requirements

- Docker
- OpenAI API key (stored in an `.env` file)

## Setup Guide

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Build the Docker Container**:
   ```bash
   docker build -t legate .
   ```

3. **Environment Variables**:
   - Ensure your `.env` file is in the root directory and defines your OpenAI API key:
     ```
     OPENAI_KEY=your_openai_api_key
     ```

4. **Run the Docker Container**:
   ```bash
   docker run --env-file .env -it legate
   ```

## Usage

Once inside the container, the assistant will be ready to receive prompts, and it will generate responses dynamically. Interact with it by entering text prompts, and it will engage in an interactive session until you terminate.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
