from bs4 import BeautifulSoup

print_raw = False

# Step 1: Load the HTML file
# file = 'input/offers_2025-07-23T12_53_33.146Z.html'
file = 'input/offers_a.html'
with open(file, 'r', encoding='utf-8') as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, 'html.parser')
screen_root = soup.find('div', id='screen-root')

if not screen_root:
    print("No <div id='screen-root'> found.")
    exit()

# Extract text after SORT
lines = screen_root.get_text(separator='\n', strip=True).splitlines()
try:
    sort_index = next(i for i, line in enumerate(lines) if "SORT" in line) + 1
    lines = lines[sort_index:]
except StopIteration:
    print("'SORT' not found.")
    exit()

if print_raw:
    print("\n--- RAW TEXT AFTER 'SORT' ---\n")
    for line in lines:
        print(line)
    exit()

# Parsing offers
offers = []
i = 0
expecting_user = True

while i < len(lines):
    # Get user
    if expecting_user:
        user = lines[i]
        i += 1
        expecting_user = False
    else:
        if lines[i] in ("Write an answer…", "Write a comment…"):
            i += 1
            if i < len(lines):
                user = lines[i]
                i += 1
            else:
                break
        else:
            i += 1
            continue

    # Find time
    time = None
    while i < len(lines):
        if '󰞋󱙫' in lines[i]:
            time = lines[i]
            i += 1
            break
        i += 1

    # Find start of details
    while i < len(lines) and '󰟝' not in lines[i]:
        i += 1
    i += 1  # skip the 󰟝 line

    # Gather details until 󰍸
    details = []
    while i < len(lines) and '󰍸' not in lines[i]:
        details.append(lines[i])
        i += 1
    i += 1  # skip 󰍸

    offers.append({
        'user': user,
        'time': time,
        'details': details
    })

# Output
for idx, offer in enumerate(offers, 1):
    print(f"\n--- Offer {idx} ---")
    print("User:", offer['user'])
    print("Time:", offer['time'])
    print("Details:")
    for line in offer['details']:
        print("  ", line)
