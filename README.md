# Interview-AI-Human

This repository contains the Python code for an AI-based interview system designed for a research project on social desirability bias in human-AI communication.

The goal of this project is to build a structured interview engine where the overall interview topics are fixed, but the follow-up questions are generated adaptively based on the participant's answers.

## Project Overview

The interview system is designed to compare responses collected through an AI interviewer with responses collected through a human interviewer.

The AI interviewer follows a structured interview guide. The main topics are the same across participants, but the follow-up questions can change depending on what the participant says.

The system uses GPT as the main reasoning engine. ElevenLabs is used only for the voice interface. In other words, ElevenLabs handles the speaking part, but the actual interview logic and question generation come from GPT.

## How the Interview Works

The interview has a fixed structure:

1. Opening and introduction
2. General questions about giving and donation behavior
3. Follow-up questions based on the participant's answers
4. Questions about trust, social pressure, and honesty
5. A hypothetical donation decision
6. Closing question

The AI does not simply ask a fixed list of questions. Instead, it uses the participant's previous answer to decide what follow-up question should be asked next.

## Main Features

- Structured interview flow
- Adaptive follow-up questions
- Topic-based interview design
- GPT-powered question generation
- Compatible with voice interface through ElevenLabs
- Can be tested locally in Python
- Designed for research on social desirability bias

## Files

- `interview_engine.py`: Main Python script for running the interview logic
- `README.md`: Project description and instructions

## Research Purpose

This project is part of a research design that studies whether people respond differently when they are interviewed by an AI interviewer compared to a human interviewer.

The broader research question is whether AI interviews reduce or increase socially desirable responding, especially in contexts involving generosity, honesty, and donation behavior.

## Technical Structure

The code is organized around a structured interview guide. Each topic has:

- A main question
- Possible adaptive follow-up questions
- Transition logic
- A closing step

The GPT model is used to generate natural and context-sensitive follow-up questions while keeping the interview within the planned research structure.

## Current Status

The current version runs locally in Python and can be tested through the command line. The next step is to connect it to ElevenLabs for a voice-based interview experience.
