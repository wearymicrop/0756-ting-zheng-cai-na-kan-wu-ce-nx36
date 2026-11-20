const sampleSelect = document.querySelector('#sample');
sampleSelect.addEventListener('change', () => {
  const url = new URL(window.location.href);
  url.searchParams.set('sample', sampleSelect.value);
  window.location.assign(url);
});

const locator = document.querySelector('#anchor-select');
if (locator) {
  const spreads = Array.from(document.querySelectorAll('[data-folio]'));
  locator.addEventListener('change', () => {
    for (const spread of spreads) spread.hidden = spread.dataset.folio !== locator.value;
  });
}
