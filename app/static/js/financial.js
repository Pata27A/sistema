document.addEventListener('DOMContentLoaded', function() {
  // Validar formularios antes de enviar
  
  const validarFechas = (desde, hasta) => {
    if (!desde || !hasta) {
      alert('Por favor ingrese ambas fechas.');
      return false;
    }
    if (desde > hasta) {
      alert('La fecha "Desde" no puede ser mayor que "Hasta".');
      return false;
    }
    return true;
  };

  // Flujo de Caja
  const formFlujoCaja = document.getElementById('formFlujoCaja');
  formFlujoCaja.addEventListener('submit', function(e) {
    const desde = this.fecha_desde.value;
    const hasta = this.fecha_hasta.value;
    if (!validarFechas(desde, hasta)) e.preventDefault();
  });

  // Rentabilidad
  const formRentabilidad = document.getElementById('formRentabilidad');
  formRentabilidad.addEventListener('submit', function(e) {
    const desde = this.fecha_desde.value;
    const hasta = this.fecha_hasta.value;
    if (!validarFechas(desde, hasta)) e.preventDefault();
  });

  // Compras por Proveedor
  const formComprasProveedor = document.getElementById('formComprasProveedor');
  formComprasProveedor.addEventListener('submit', function(e) {
    const includeAll = this.include_all.checked;
    const supplier = this.supplier_id.value;
    if (!includeAll && !supplier) {
      alert('Por favor seleccione un proveedor o marque "Incluir todos los proveedores".');
      e.preventDefault();
    }
  });
});
