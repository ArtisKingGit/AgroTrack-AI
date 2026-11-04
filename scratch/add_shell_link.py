import os

pages = ['dashboard.html', 'manage.html', 'recommendations.html', 'expenses.html', 'history.html', 'settings.html']

for page in pages:
    fpath = os.path.join('frontend', page)
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        c = f.read()

    target = '<nav class="nav">'
    replacement = '<nav class="nav">\n        <a href="overview.html" style="background: rgba(34, 197, 94, 0.15); color: #22c55e; font-weight: 600; border: 1px solid rgba(34, 197, 94, 0.3);"><i class="fas fa-grid-2"></i> <span>AgroTrack AI</span></a>'
    
    if 'href="overview.html"' not in c and target in c:
        c = c.replace(target, replacement, 1)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Added AgroTrack AI link to {page}")
    else:
        print(f"Skipped {page} (already present or target not found)")
