// webapp/static/js/stats/latest.js
//
// Stale-response guard for async fetches: only the most recently started task counts. An older task that
// finishes late (success OR failure) is reported as stale, so it can neither overwrite newer data nor show
// an error over it. Pure, no DOM.

export function createLatestGuard() {
  let latest = 0;
  return {
    // Runs `task` and resolves to { current: true, value } when it is still the newest, or { current: false }
    // when a newer run started meanwhile. A failure is thrown only if the task is still the newest.
    async run(task) {
      const mine = ++latest;
      try {
        const value = await task();
        return mine === latest ? { current: true, value } : { current: false };
      } catch (err) {
        if (mine !== latest) return { current: false };
        throw err;
      }
    },
  };
}
