// charts._anchor: the name of a record's row (#w-…). Its own module so the figures
// that run in the browser (public/figs/) can use it without the Worker-only modules.
export const anchor = workKey => workKey.replace(/[^0-9A-Za-z぀-ヿ一-鿿-]/gu, '_').slice(0, 80);
