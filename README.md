# Substio_APP

## Places
 - courthouse (https://dane.gov.pl/pl/dataset/985,lista-sadow-powszechnych/resource/67369/table)
 - prison
 - police

```bash
cd tools
uv run offers.py
cd ..
```
## Data fetching: combined Script (Scroll → Expand → Export)
```bash
https://www.facebook.com/groups/zleceniaprawne/?sorting_setting=CHRONOLOGICAL
```

```js
  const now = new Date();
  const fileName = `facebook_page_${now.toISOString()}.html`;

  // Step 5: Save full HTML
  const html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
  const blob = new Blob([html], { type: 'text/html' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  a.click();
```

```js
  document.querySelectorAll('*').forEach(el => {
    if (
      el.textContent.trim().toLowerCase() === 'see more' &&
      el.offsetParent !== null &&
      typeof el.click === 'function'
    ) {
      el.click();
    }
  });
```

```js
(async () => {
  const delay = 300; // ms between actions
  const isVisible = el => el.offsetParent !== null;
  const isClickable = el => !el.hasAttribute('disabled') && el.href;

  const visibleLinks = Array.from(document.querySelectorAll('a'))
    .filter(el => isVisible(el) && isClickable(el));

  for (const link of visibleLinks) {
    link.scrollIntoView({ behavior: 'smooth', block: 'center' });
    link.focus();
    
    // Symulacja hover: mouseover + mouseenter
    ['mouseover', 'mouseenter'].forEach(evtType => {
      link.dispatchEvent(new MouseEvent(evtType, { bubbles: true, cancelable: true }));
    });

    console.log(link.href);
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  console.log('Hover i focus na wszystkich widocznych linkach zakończone.');
})();

```

```js
(async () => {
  const delay = 300; // ms between focus
  const isVisible = el => el.offsetParent !== null;

  const visibleLinks = Array.from(document.querySelectorAll('a'))
    .filter(isVisible);

  for (const link of visibleLinks) {
    link.scrollIntoView({ behavior: 'smooth', block: 'center' });
    link.focus();
    console.log(link.href);
    await new Promise(resolve => setTimeout(resolve, delay));
  }
})();
```





```js
  document.querySelectorAll('*').forEach(el => {
    if (
      el.textContent.trim().toLowerCase() === 'see more' &&
      el.offsetParent !== null &&
      typeof el.click === 'function'
    ) {
      el.click();
    }
  });

  await new Promise(resolve => setTimeout(resolve, 1000));
  
(async function scrollAndExport(times = 5, delay = 1500) {
  // Step 1: Scroll the page down multiple times
  for (let i = 0; i < times; i++) {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    await new Promise(resolve => setTimeout(resolve, delay));
  }

  // Step 2: Click all "see more" buttons or links, robust version
  document.querySelectorAll('*').forEach(el => {
    if (
      el.textContent.trim().toLowerCase() === 'see more' &&
      el.offsetParent !== null &&
      typeof el.click === 'function'
    ) {
      el.click();
    }
  });

  // Step 3: Optional wait for content expansion
  await new Promise(resolve => setTimeout(resolve, 10000));

  // Step 4: Create filename using raw timestamp
  const now = new Date();
  const fileName = `facebook_page_${now.toISOString()}.html`;

  // Step 5: Save full HTML
  const html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
  const blob = new Blob([html], { type: 'text/html' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  a.click();
})();

```

## Docker

```bash
COMPOSE_BAKE=true docker compose build
```

## Migrations

New migration

```bash
alembic revision -m "create XXX table"
```

> [!NOTE]  
> Run below commands inside a docker container

Check current revision

```bash
docker exec -it substio_app .venv/bin/alembic current
```

To run all of your outstanding migrations, execute the `upgrade head` command

```bash
docker exec -it substio_app .venv/bin/alembic upgrade head
```

To roll back the latest migration operation, you may use the `alembic downgrade` command

```bash
docker exec -it substio_app .venv/bin/alembic downgrade -1
```

To run rolled back migration again:

```bash
docker exec -it substio_app .venv/bin/alembic upgrade +1
```

Revision History: Use `.venv/bin/alembic history` to see the history of migrations and understand the steps involved.
Detailed View: Use `.venv/bin/alembic show <revision>` to get detailed information about specific revision scripts.

## Update python dependencies

```bash
uv lock --upgrade
```

clean cache

```bash
uv cache clean
```

### Check & format project

```bash
ruff check app/
```

```bash
ruff check app/ --fix
```

## Cold start

- alembic migration
- insert geo data `uv run locations.py`

### Truncate PG data

```postgresql
TRUNCATE TABLE locations RESTART IDENTITY CASCADE;
```

### LLM friendly version

```bash
bunx repomix --style markdown --ignore "**/*.log,tmp/,Readme.md,uv.lock"
```
