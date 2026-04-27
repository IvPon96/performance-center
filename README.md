# 🌐 Global Operations Center | Analytics Engine

> A real-time data monitoring and behavioral analytics system built to track system workloads, optimize team execution, and detect operational bottlenecks in a BPO environment.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.20+-FF4B4B.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Manipulation-150458.svg)
![Plotly](https://img.shields.io/badge/Plotly-Data_Visualization-3F4F75.svg)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Profile-0A66C2?logo=linkedin)](https://www.linkedin.com/in/ivan-ponce-rodriguez-8640832ba)
---

## 📖 The Context & The Problem
In outsourced operations (BPO), managing a team's productivity often feels like operating a "black box". The standard metrics (total calls, total hours) are easy to manipulate and fail to show the true quality of the effort. 

**The main challenges were:**
1. **Redundant Efforts:** Agents repeatedly contacting unresponsive entities to inflate their volume metrics.
2. **Disconnected Data:** Workloads lived in one system (Inbound Queue), execution lived in another (Telephony/Outreach), and attendance in another.
3. **Behavioral Blind Spots:** Inability to correlate system pressure (high workload) with team pacing (idle times).

## 💡 The Solution
I built the **Global Operations Center**, a comprehensive full-stack analytics application using Python and Streamlit. It acts as an operational radar that shifts the focus from *quantity* of work to *quality* of execution.

### ✨ Key Features
* **The "Neural Backbone" Engine:** A custom data-processing module that simultaneously fetches, cleans, and merges data from three different disconnected sources in milliseconds.
* **Workload vs. Execution Tracking:** Side-by-side historical trend analysis to ensure team output correlates with system demands.
* **Bottleneck Detection (High Friction Radar):** An algorithm that identifies entities receiving excessive outreach attempts with minimal productive time, saving hours of wasted labor.
* **Behavioral Audit Profiles:** Individual drill-down dashboards that detect patterns like "IVR camping" or strategic idle times during peak workload hours.

## 🏗️ Architecture & Data Pipeline
The application runs on a robust backend architecture:
1. **Extraction:** Automated extraction of daily operational logs via secure endpoints.
2. **Transformation:** - Complex datetime manipulation (Timezone offsets, DST adjustments).
   - Regex cleaning of numeric fields and string parsing.
   - Categorization of operational gaps (e.g., differentiating scheduled breaks from unexplained idle time).
3. **Load & Visualization:** Interactive, state-managed UI components rendered via Streamlit and Plotly.

*(Note: All data in this repository has been thoroughly anonymized through a custom ETL pipeline to protect sensitive corporate information while preserving mathematical correlations).*

## 🚀 How to Run Locally

1. Clone the repository:
   ```bash
   git clone [https://github.com/IvPon96/performance-center.git](https://github.com/IvPon96/performance-center.git)

2. Navigate to the project directory:
    cd performance-center

3. Install dependencies:
    pip install -r requirements.txt

4. Run the Streamlit application
    streamlit run app.py

## 🧠 Impact & Results
By deploying this engine, operations managers transitioned from reactive, "feeling-based" management to **data-driven leadership**. The dashboard successfully exposed redundant behaviors, allowing management to recalibrate KPIs and increase the actual productive capacity of the team without increasing headcount.

---
### 📬 Let's Connect!
*Built with data engineering principles by [Iván Ponce Rodríguez](https://www.linkedin.com/in/ivan-ponce-rodriguez-8640832ba).*

Feel free to reach out on LinkedIn if you want to discuss data analytics, operations optimization, or this project!