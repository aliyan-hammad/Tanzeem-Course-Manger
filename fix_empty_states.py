import re
import os

files = {
    'templates/students.html': 'Students Management',
    'templates/attendance.html': 'Attendance Management',
    'templates/fees.html': 'Fee Collections',
    'templates/expenses.html': 'Expense Log'
}

for file_path, title in files.items():
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, 'r') as f:
        content = f.read()
        
    if '{% if not courses %}' in content:
        continue

    empty_state_block = f"""{{% block content %}}
{{% if not courses %}}
<div class="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
    <h2 class="mb-0">{title}</h2>
</div>
<div class="alert alert-info text-center shadow-sm border-0 rounded-3 mt-5 p-5">
    <i class="bi bi-journal-x display-1 text-info d-block mb-3 opacity-50"></i>
    <h3 class="alert-heading fw-bold text-dark mb-3">No Courses Assigned Yet</h3>
    <p class="text-muted fs-5 mb-0">Your workspace is ready, but you haven't been assigned to any active courses yet. Once an administrator assigns a course to your account, you will be able to manage everything right here.</p>
</div>
{{% else %}}"""

    # Replace the block content start with our empty state block
    content = re.sub(r'\{%\s*block\s+content\s*%\}', empty_state_block, content, count=1)
    
    # Append {% endif %} just before {% endblock %}
    content = re.sub(r'\{%\s*endblock\s*%\}', r'{% endif %}\n{% endblock %}', content)
    
    with open(file_path, 'w') as f:
        f.write(content)
        
print("Empty states added.")
