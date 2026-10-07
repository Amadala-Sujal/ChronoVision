\# ChronoVision



ChronoVision is an AI-powered video understanding and temporal reasoning system built for HackNEX 2026 Problem Statement HNX26PSI02.



Instead of only detecting objects in individual frames, ChronoVision analyzes events over time, tracks entities, builds a temporal event timeline, and answers questions about what happened, when it happened, and the order of events.



\## Problem Statement



HNX26PSI02 — Video Understanding \& Temporal Reasoning



\## What ChronoVision Does



ChronoVision processes video through the following pipeline:



Video

→ Object Detection

→ Multi-Object Tracking

→ Event Extraction

→ Temporal Event Timeline

→ Question Router

→ Semantic Reasoning

→ Timestamped Answer + Evidence



The system can reason about:



\- Event order

\- Before / after relationships

\- Event duration

\- Movement

\- Restricted-zone activity

\- Person/object interactions

\- Stationary behavior

\- Timestamped evidence

\- Semantic video events



\## Key Features



\- YOLO-based object detection

\- BoT-SORT multi-object tracking

\- Re-identification support

\- Temporal event extraction

\- Movement start/stop detection

\- Restricted-zone reasoning

\- Interaction detection

\- Stationary / untouched-object reasoning

\- Natural-language temporal queries

\- Timestamped answers

\- Evidence frame and video clip generation

\- Gemini-based semantic video understanding

\- Streamlit dashboard

\- Fine-tuned construction-safety detector



\## Technologies



\- Python

\- YOLO26

\- BoT-SORT

\- OpenCV

\- FFmpeg

\- Streamlit

\- Google Gemini API

\- Pydantic



\## External Resources



\### Dataset



Construction Site Safety dataset, Roboflow Universe, Version 28.



The dataset contains classes including:



\- Person

\- Machinery

\- Vehicle

\- Hardhat

\- Mask

\- NO-Hardhat

\- NO-Mask

\- Safety Vest

\- NO-Safety Vest

\- Safety Cone



License: CC BY 4.0



\### Pretrained Models



\- YOLO26 pretrained model

\- BoT-SORT tracking components



\### External API



\- Google Gemini API for semantic video understanding



All external datasets, pretrained models, APIs, and open-source components are declared as required by the HackNEX submission guidelines.



\## Installation



Create a Python environment and install the required dependencies.



```bash

pip install -r requirements.txt

