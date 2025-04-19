import streamlit as st
import pandas as pd

st.write("my first app  hello world")

st.write("hello  kamal lon")
st.title("this is title")  

table = ({"columnn 1" : [1,2, 3, 4, 5],
          "columne 2" : [6, 7, 8 , 9, 10]})

st.dataframe(table) 