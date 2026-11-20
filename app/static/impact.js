const impactConsole = document.querySelector('.impact-console');

if (impactConsole) {
  const runId = impactConsole.dataset.run;
  const statusLine = impactConsole.querySelector('.impact-status');
  const buttons = impactConsole.querySelectorAll('button');

  async function call(url, body) {
    buttons.forEach(button => { button.disabled = true; });
    statusLine.textContent = '正在整理旧案卷…';
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body || {}),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.message || '操作失败');
      statusLine.textContent = '影响册已更新，正在刷新…';
      const urlNow = new URL(window.location.href);
      urlNow.searchParams.set('run', runId);
      window.location.assign(urlNow.toString());
    } catch (error) {
      statusLine.textContent = error.message || '影响册操作失败。';
      buttons.forEach(button => { button.disabled = false; });
    }
  }

  impactConsole.querySelector('.impact-recompute')
    .addEventListener('click', () => call(`/api/runs/${runId}/impact/recompute`));
  impactConsole.querySelector('.impact-dispatch')
    .addEventListener('click', () => call(`/api/runs/${runId}/impact/dispatch`, {opinion_ids: []}));
}
