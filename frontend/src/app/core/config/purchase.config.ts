export const PURCHASE_CONFIG = {
  // Reemplaza este valor por el número real con código de país, sin + ni espacios.
  whatsappNumber: '519XXXXXXXX',
  deliveryCost: 10,
  payment: {
    Yape: {
      holder: 'NOMBRE DEL TITULAR YAPE',
      phone: '9XX XXX XXX',
      // Coloca el archivo real en frontend/public y usa una ruta como /qr-yape.png.
      qrUrl: '',
    },
    Plin: {
      holder: 'NOMBRE DEL TITULAR PLIN',
      phone: '9XX XXX XXX',
      // Coloca el archivo real en frontend/public y usa una ruta como /qr-plin.png.
      qrUrl: '',
    },
  },
} as const;
