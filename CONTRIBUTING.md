# 🤝 Contributing Guide

Hey there! Thanks for showing interest in contributing to this project. Whether you're fixing a bug, improving docs, or building a new feature — you're amazing. Here's everything you need to get started.

---

## 📦 Before You Start

### 1. **Fork & Clone the Repo**

```bash
git clone https://github.com/your-username/api-monitoring-system.git
cd api-monitoring-system
````

### 2. **Set Up Your Environment**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

> ✏️ Fill in your `.env` file with the necessary config. MongoDB Atlas and Elastic Cloud credentials are required.

---

## 🚧 What You Can Work On

* 🐞 Fix bugs and file issues
* ✨ Suggest and build new features
* 🧪 Add tests or improve coverage
* 🧠 Enhance the anomaly detection logic
* 📈 Improve the performance of queries
* 🧾 Help improve the documentation

If you're unsure where to start, check out the [Issues](https://github.com/santosharron/api-monitoring-system/issues) tab — especially the ones labeled `good first issue`.

---

## 🛠 How to Make a Contribution

### 1. **Create a New Branch**

```bash
git checkout -b feature/your-feature-name
```

Keep it focused! One feature or fix per branch 🙏

### 2. **Make Your Changes**

Write clean, readable code. If you’re touching logic-heavy areas, don’t forget to add tests!

### 3. **Run the Tests**

```bash
pytest tests/
```

Fix any errors before pushing your changes.

### 4. **Commit Smartly**

Use descriptive commit messages:

```bash
git commit -m "fix: handle empty response from API checker"
```

### 5. **Push and Open a PR**

```bash
git push origin feature/your-feature-name
```

Then, head over to GitHub and open a pull request into the `main` branch.

<Alert variant="default">
If your PR closes an issue, mention it like this:  
<code>Closes #123</code>
</Alert>

---

## 🔐 Found a Security Issue?

Please don’t open a public issue.
Email me or open a private discussion through GitHub to report the vulnerability discreetly.

More on this in [`SECURITY.md`](./SECURITY.md)

---

## 👏 Thanks Again!

You’re helping make API monitoring smarter and more reliable.
I appreciate your time, effort, and energy — welcome to the contributor family!

