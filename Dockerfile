FROM python:3

# Install dependencies.
ADD requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# Copy code.
COPY ./main.py .

CMD python /main.py
