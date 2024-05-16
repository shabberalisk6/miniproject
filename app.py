# Importing Libraries
import streamlit as st
import base64
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse
from textwrap import dedent
from transformers import BartForConditionalGeneration, BartTokenizer
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
from heapq import nlargest

# Streamlit Configuration
st.set_page_config(
    page_title="Youtube Summariser",
    page_icon='favicon.ico',
    layout="wide",
    initial_sidebar_state="expanded",
    )

# Function to Summarize using Spacy
def spacy_summarize(text_content, percent):
    stop_words = list(STOP_WORDS)
    punctuation_items = punctuation + '\n'
    nlp = spacy.load('en_core_web_sm')

    nlp_object = nlp(text_content)
    word_frequencies = {}
    for word in nlp_object:
        if word.text.lower() not in stop_words and word.text.lower() not in punctuation_items:
            if word.text not in word_frequencies.keys():
                word_frequencies[word.text] = 1
            else:
                word_frequencies[word.text] += 1

    max_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency

    sentence_token = [sentence for sentence in nlp_object.sents]
    sentence_scores = {}
    for sent in sentence_token:
        sentence = sent.text.split(" ")
        for word in sentence:
            if word.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.lower()]

    select_length = int(len(sentence_token) * (int(percent) / 100))
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word.text for word in summary]
    summary = ' '.join(final_summary)
    return summary

# Function to Summarize using BART
def bart_summarize(text_content, max_length=150):
    tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
    model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

    inputs = tokenizer.encode("summarize: " + text_content, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(inputs, max_length=max_length, min_length=max_length//2, length_penalty=2.0, num_beams=4, early_stopping=True)

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

# Hide Streamlit Footer and buttons
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.css-1l02zno {padding: 0 !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Adding logo for the App
file_ = open("app_logo.gif", "rb")
contents = file_.read()
data_url = base64.b64encode(contents).decode("utf-8")
file_.close()

st.sidebar.markdown(
    f'<img src="data:image/gif;base64,{data_url}" alt="" style="height:300px; width:400px;">',
    unsafe_allow_html=True,
)

# Set background color
st.markdown(
    """
    <style>
    body {
        background-color: #f0f2f6;
    }
    .summary-container {
        border: 1px solid #ccc;
        border-radius: 10px;
        padding: 20px;
        background-color: #ADD8E6;
        margin-bottom: 20px;
    }
    .summary-container h3 {
        color: #333;
    }
    .summary-container p {
        color: #555;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Input Video Link
url = st.sidebar.text_input('Video URL', 'https://www.youtube.com/watch?v=T-JVpKku5SI')

# Display Video and Title
r = requests.get(url)
soup = BeautifulSoup(r.text, features="html.parser")
link = soup.find_all(name="title")[0]
title = str(link).replace("<title>","").replace("</title>","").replace("&amp;","&")
st.info("### " + title)
st.video(url)

# Specify Summarization type
sumtype = st.sidebar.selectbox(
    'Specify Summarization Type',
    options=['Extractive', 'Abstractive (Subtitles)'],
    index=0,
    disabled=False
)

if sumtype == 'Extractive':
    # Specify the summary length
    length = st.sidebar.select_slider(
        'Specify length of Summary',
        options=['10%', '20%', '30%', '40%', '50%']
    )

    if st.sidebar.button('Summarize'):
        st.success("### Success! Extractive summary generated.")

        # Generate Transcript by slicing YouTube link to id
        url_data = urlparse(url)
        id = url_data.query[2::]

        def generate_transcript(id):
            transcript = YouTubeTranscriptApi.get_transcript(id)
            script = ""
            for text in transcript:
                t = text["text"]
                if t != '[Music]':
                    script += t + " "
            return script, len(script.split())

        transcript, no_of_words = generate_transcript(id)

        # Generate summary using Spacy
        summ = spacy_summarize(transcript, int(length[:2]))

        # Translate and Print Summary
        st.markdown(dedent(f"""
        <div class="summary-container">
            <h3>\U0001F4D6 Summary</h3>
            <p>{summ}</p>
        </div>
        """), unsafe_allow_html=True)

elif sumtype == 'Abstractive (Subtitles)':
    if st.sidebar.button('Summarize'):
        st.success("### Success! Subtitles generated.")

        # Generate Transcript by slicing YouTube link to id
        url_data = urlparse(url)
        id = url_data.query[2::]

        def generate_transcript(id):
            transcript = YouTubeTranscriptApi.get_transcript(id)
            script = ""
            for text in transcript:
                t = text["text"]
                if t != '[Music]':
                    script += t + " "
            return script, len(script.split())

        transcript, no_of_words = generate_transcript(id)

        # Display subtitles inside a bordered container
        st.markdown(dedent(f"""
        <div class="summary-container">
            <h3>\U0001F3A5 Subtitles</h3>
            <p>{transcript}</p>
        </div>
        """), unsafe_allow_html=True)

# Add Sidebar Info
st.sidebar.info(
    dedent(
        """
        This web app is made by\n
        TEAM - 4
        """
    )
)
