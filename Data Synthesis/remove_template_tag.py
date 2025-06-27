import re

def remove_template_tags(text):
    # Remove all <Template_...>...</Template_...> tags and keep their inner content
    cleaned_text = re.sub(r'<Template_[^>]+>(.*?)<\/Template_[^>]+>', r'\1', text, flags=re.DOTALL)
    return cleaned_text

file_path = 'Case_23_Suspect_1_Intelligence_1_CrossBorder.md'

try:
    with open(file_path, 'r', encoding='utf-8') as file:
        input_text = file.read()
    output_text = remove_template_tags(input_text)
    print(output_text)
except FileNotFoundError:
    print('Error: File not found:', file_path)
