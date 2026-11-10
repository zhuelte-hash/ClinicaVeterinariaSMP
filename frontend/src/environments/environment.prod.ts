export const environment = {
  production: true,
  // En producción el frontend y la API deben compartir dominio o proxy inverso.
  // Local conserva el puerto separado usado por compose/dev.
  apiUrl: typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000' : '',
  useAdminMockData: false,
};
