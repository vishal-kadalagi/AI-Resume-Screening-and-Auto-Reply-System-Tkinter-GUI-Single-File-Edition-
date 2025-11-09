# 🧠 AI Resume Screening & Auto-Reply System (Tkinter GUI)

An AI-powered desktop application that automates resume screening and reply drafting — all in a single Python file.  
It analyzes resumes, matches candidate skills with your requirements, classifies them (✅ Suitable / ⚠ Maybe / ❌ Reject), and generates smart, editable email replies for each applicant.

---

## 🚀 Features

- 📂 **Upload Multiple Resumes** (.pdf, .docx, .txt)
- 🧠 **Keyword-Based Skill Matching**
- 🎯 **Smart Classification Rules**
  - ✅ **Suitable:** match ≥ 70%
  - ⚠ **Maybe:** 40% ≤ match < 70%
  - ❌ **Reject:** match < 40% or missing critical skills
- 🟩 **Color-coded Results View** (green/orange/red)
- 📨 **Auto-Generate Professional Reply Templates**
- 💾 **Save & Load Reply Drafts**
- 📊 **Export Results to CSV**
- 🪶 **Beautiful Tkinter GUI**

---

## 🧰 Requirements

Install dependencies using pip:

```bash
pip install PyPDF2 python-docx
