import re

with open('templates/base.html', 'r') as f:
    content = f.read()

# 1. Update sidebar header
old_sidebar_header = r'<div class="sidebar-header p-3 mb-3 border-bottom border-secondary text-center">\s*<img src="\{\{ url_for\(\'static\', filename=\'logo\.png\'\) \}\}" alt="Logo" class="img-fluid w-100 mb-2" style="object-fit: contain;">\s*<h5 class="mb-0 text-white fw-bold">Tanzeem-e-Islami</h5>\s*</div>'
new_sidebar_header = """<div class="sidebar-header p-3 mb-3 border-bottom border-secondary text-center">
            {% if current_user.role == 'Admin' %}
                <i class="bi bi-shield-lock text-primary mb-2" style="font-size: 2.5rem;"></i>
                <h5 class="mb-0 text-white fw-bold">Admin Panel</h5>
            {% else %}
                <i class="bi bi-briefcase text-info mb-2" style="font-size: 2.5rem;"></i>
                <h5 class="mb-0 text-white fw-bold">Coordinator Panel</h5>
            {% endif %}
        </div>"""
content = re.sub(old_sidebar_header, new_sidebar_header, content, flags=re.MULTILINE)

# 2. Append profile to bottom of sidebar
old_nav_end = r'</ul>\s*</nav>'
new_nav_end = """</ul>
        <div class="mt-auto p-3 border-top border-secondary bg-dark bg-opacity-25">
            <div class="d-flex align-items-center mb-3 text-white">
                <i class="bi bi-person-circle fs-3 me-2"></i>
                <div class="text-start">
                    <h6 class="mb-0 fw-bold">{{ current_user.full_name if current_user.full_name else current_user.username }}</h6>
                    <small class="text-light">{{ current_user.role }} Workspace</small>
                </div>
            </div>
            <a href="{{ url_for('auth.logout') }}" class="btn btn-sm btn-outline-danger w-100 text-nowrap">
                <i class="bi bi-box-arrow-right"></i> Logout
            </a>
        </div>
    </nav>"""
content = re.sub(old_nav_end, new_nav_end, content, flags=re.MULTILINE)

# 3. Update top navbar to remove right-side elements
old_top_navbar = r'<div class="d-flex align-items-center gap-2">\s*<span class="badge bg-primary rounded-pill p-2 d-none d-sm-block"><i class="bi bi-person-circle"></i> \{\{ current_user\.username \}\}</span>\s*<a href="\{\{ url_for\(\'auth\.logout\'\) \}\}" class="btn btn-sm btn-outline-danger text-nowrap">\s*<i class="bi bi-box-arrow-right"></i> <span class="d-none d-sm-inline">Logout</span>\s*</a>\s*</div>'
content = re.sub(old_top_navbar, '', content, flags=re.MULTILINE)

# 4. Update CSS for active link
old_css_active = r'\.sidebar \.nav-link:hover, \.sidebar \.nav-link\.active \{\s*background-color: #495057;\s*color: white;\s*\}'
new_css_active = """.sidebar .nav-link:hover {
            background-color: #495057;
            color: white;
        }
        .sidebar .nav-link.active {
            background-color: #3b4248;
            color: white;
            border-left: 4px solid #0d6efd;
        }"""
content = re.sub(old_css_active, new_css_active, content, flags=re.MULTILINE)

with open('templates/base.html', 'w') as f:
    f.write(content)
