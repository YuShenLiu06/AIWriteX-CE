// Global fetch interceptor: redirect to /login when any API call returns 401.
// Observes the response only — does NOT modify request URLs or add headers.
// Guards prevent a redirect loop on the login page / login call itself.
(function () {
  var _fetch = window.fetch;
  window.fetch = function (input, init) {
    return _fetch.call(this, input, init).then(function (resp) {
      try {
        var url = (typeof input === 'string') ? input : (input && input.url) || '';
        // never redirect for the login endpoint itself or while on the login page
        if (resp.status === 401 &&
            location.pathname.indexOf('/login') !== 0 &&
            url.indexOf('/api/auth/login') === -1) {
          window.location.replace('/login');
        }
      } catch (e) {}
      return resp;
    });
  };
})();
