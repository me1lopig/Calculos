# Geocempy Streamlit

## 1) Install dependencies

```powershell
pip install -r requirements.txt
```

## 2) Run app

```powershell
streamlit run streamlit_app.py
```

## 3) Use the web app

1. Upload XLSX files in the UI.
2. Required base files:
   - `BKFL.XLSX`
   - `DPRG.XLSX`
   - `ISPT.XLSX`
   - `ListadoLab.XLSX`
3. Optional file:
   - `UGEO.XLSX` (required only if `Representar Unidades Geotecnicas` is enabled)
4. Select one or more profile files from `Perfiles`.
5. Click `Generar DXF`.
6. Click `Descargar DXF` to download the generated file.
