from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    upload_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class Summary(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE)
    text = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Summary of {self.document.title}"

class AudioFile(models.Model):
    summary = models.OneToOneField(Summary, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    voice_type = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Audio for {self.summary.document.title}"

class Question(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question_text = models.TextField()
    answer_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.question_text[:50]