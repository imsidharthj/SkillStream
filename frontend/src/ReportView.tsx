import { useState } from "react";
import type { Report } from "./api";

export default function ReportView({ report }: { report: Report }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = `${window.location.origin}/?transcript=${report.session_id}`;

  async function copy() {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
  }

  return (
    <section className="panel report">
      <div className="share">
        <b>Share the transcript with the candidate</b>
        <div className="row">
          <input readOnly value={shareUrl} onFocus={(e) => e.target.select()} />
          <button onClick={copy}>{copied ? "Copied" : "Copy link"}</button>
        </div>
        <p className="muted">The candidate sees only the transcript, not the report or scores.</p>
      </div>
      <p className="warning">Automated draft — requires human review. Scores are not a hiring decision.</p>
      <h2>Summary</h2>
      <p>{report.summary}</p>

      <h2>Questions and answers</h2>
      {report.questions_and_answers.map((qa, i) => (
        <div key={i} className="qa"><b>{qa.question}</b><p>{qa.answer}</p></div>
      ))}

      <h2>Key strengths</h2>
      <ul>{report.key_strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>

      <h2>Missing information</h2>
      {report.missing_information.length ? (
        <ul>{report.missing_information.map((s, i) => <li key={i}>{s}</li>)}</ul>
      ) : <p className="muted">Nothing missing.</p>}

      <h2>Rubric scores (evidence-based)</h2>
      {report.rubric_scores.length ? (
        <table>
          <thead><tr><th>Category</th><th>Score</th><th>Evidence</th></tr></thead>
          <tbody>{report.rubric_scores.map((r, i) => (
            <tr key={i}><td>{r.category}</td><td>{r.score}/5</td><td>{r.evidence}</td></tr>
          ))}</tbody>
        </table>
      ) : <p className="muted">No scores with sufficient evidence.</p>}

      <h2>Draft final answers</h2>
      <dl>{report.draft_final_answers.map((a) => (
        <div key={a.field}><dt>{a.field}</dt><dd>{a.answer}</dd></div>
      ))}</dl>

      <h2>Transcript</h2>
      <div className="transcript">
        {report.transcript.map((t, i) => <p key={i} className={t.role}><b>{t.role}:</b> {t.text}</p>)}
      </div>
      <p className="muted">Session {report.session_id} · saved to data/sessions/{report.session_id}/report.json</p>
    </section>
  );
}
