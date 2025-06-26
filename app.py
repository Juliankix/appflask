from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
import os
import json

app = Flask(__name__)

# Configuración de la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo
class DataRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    value = db.Column(db.Float)
    category = db.Column(db.String(50))

    def __repr__(self):
        return f'<DataRecord {self.name}>'

# Crear tabla
with app.app_context():
    db.create_all()

@app.route('/')
def inicio():
    records = DataRecord.query.all()

    if records:
        data = {
            'id': [r.id for r in records],
            'name': [str(r.name) for r in records],
            'value': [float(r.value) for r in records],
            'category': [str(r.category) for r in records]
        }
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=['id', 'name', 'value', 'category'])

    stats = {
        'total_records': int(len(df)),
        'average_value': float(df['value'].mean()) if not df.empty else 0.0,
        'max_value': float(df['value'].max()) if not df.empty else 0.0,
        'min_value': float(df['value'].min()) if not df.empty else 0.0,
        'categories': df['category'].value_counts().to_dict() if not df.empty else {}
    }

    if df.empty:
        chart_data = {'labels': [], 'values': []}
    else:
        counts = df['category'].value_counts()
        chart_data = {
            'labels': [str(label) for label in counts.index.tolist()],
            'values': [int(value) for value in counts.values.tolist()]
        }

    chart_data_json = json.dumps(chart_data)

    return render_template('inicio.html',
                           stats=stats,
                           chart_data_json=chart_data_json,
                           records=records)

@app.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        try:
            name = str(request.form['name'])
            value = float(request.form['value'])
            category = str(request.form['category'])

            nuevo_registro = DataRecord(name=name, value=value, category=category)
            db.session.add(nuevo_registro)
            db.session.commit()
            return redirect(url_for('inicio'))
        except (ValueError, KeyError) as e:
            return f"Error en los datos: {str(e)}", 400

    return render_template('registro.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    record = DataRecord.query.get_or_404(id)

    if request.method == 'POST':
        try:
            record.name = str(request.form['name'])
            record.value = float(request.form['value'])
            record.category = str(request.form['category'])
            db.session.commit()
            return redirect(url_for('inicio'))
        except (ValueError, KeyError) as e:
            return f"Error en los datos: {str(e)}", 400

    return render_template('editar.html', record=record)

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    record = DataRecord.query.get_or_404(id)
    db.session.delete(record)
    db.session.commit()
    return redirect(url_for('inicio'))

@app.route('/analizar', methods=['POST'])
def analizar():
    try:
        records = DataRecord.query.all()

        if records:
            df = pd.DataFrame([(r.id, str(r.name), float(r.value), str(r.category))
                               for r in records],
                              columns=['id', 'name', 'value', 'category'])
        else:
            df = pd.DataFrame(columns=['id', 'name', 'value', 'category'])

        operation = request.form.get('operation', 'raw_data')

        if operation == 'summary':
            result = df.describe().to_html(classes='table table-striped')
        elif operation == 'groupby':
            result = df.groupby('category').agg({
                'value': ['mean', 'sum', 'count'],
                'id': 'count'
            }).to_html(classes='table table-striped') if not df.empty else "<p>No hay datos para agrupar</p>"
        elif operation == 'filter':
            filtered = df[df['value'] > df['value'].mean()] if not df.empty else pd.DataFrame()
            result = filtered.to_html(classes='table table-striped') if not filtered.empty else "<p>No hay datos que superen el promedio</p>"
        else:
            result = df.to_html(classes='table table-striped') if not df.empty else "<p>No hay datos disponibles</p>"

        return render_template('analisis.html',
                               table_data=result,
                               operation=operation.replace('_', ' ').title())
    except Exception as e:
        return f"Error al procesar datos: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)

