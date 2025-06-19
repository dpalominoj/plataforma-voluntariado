from datetime import datetime, date, timezone, timedelta
from werkzeug.security import generate_password_hash
from database.db import db
from model.models import Usuarios, Organizaciones, Preferencias, Discapacidades, Facilidad, Actividades, UsuarioDiscapacidad, Inscripciones, EstadoActividad

# Define peru_tz
peru_tz = timezone(timedelta(hours=-5))

def seed_data():
    # Crea organizaciones
    if Organizaciones.query.count() == 0:
        organizaciones = [
            Organizaciones(
                nombre_org="Fundación Inclusión Perú",
                descripcion_org="Organización dedicada a promover la inclusión social de personas con discapacidad",
                direccion_fisica="Av. Arequipa 123, Lima",
                logo="☺",
                fecha_registro=datetime(2025, 1, 13, 15, 0),
            ),
            Organizaciones(
                nombre_org="Manos Solidarias",
                descripcion_org="ONG enfocada en brindar apoyo a comunidades vulnerables.",
                direccion_fisica="Calle Solidaridad 456, Cusco",
                logo="♥",
                fecha_registro=datetime(2024, 11, 20, 10, 30),
            ),
            Organizaciones(
                nombre_org="Red de Voluntarios Ambientales",
                descripcion_org="Grupo dedicado a la conservación del medio ambiente y la educación ecológica.",
                direccion_fisica="Jr. Amazonas 789, Iquitos",
                logo="🌿",
                fecha_registro=datetime(2025, 2, 5, 9, 0),
            ),
             Organizaciones(
                nombre_org="Corazones Unidos por la Infancia",
                descripcion_org="Asociación que trabaja por el bienestar y desarrollo de niños en situación de riesgo.",
                direccion_fisica="Av. Los Niños 321, Trujillo",
                logo="🧒",
                fecha_registro=datetime(2024, 10, 1, 14, 15),
            ),
        ]
        db.session.add_all(organizaciones)

    # Crea discapacidades
    if Discapacidades.query.count() == 0: 
        discapacidades = [
            Discapacidades(nombre="Auditiva", descripcion="Dificultad o imposibilidad de usar el sentido del oído"), 
            Discapacidades(nombre="Visual", descripcion="Dificultad o imposibilidad de usar el sentido de la vista"), 
            Discapacidades(nombre="Motriz", descripcion="Dificultad o imposibilidad de moverse o desplazarse") 
        ]
        db.session.add_all(discapacidades)

    # Crea preferencias
    if Preferencias.query.count() == 0: 
        preferencias = [
            Preferencias(nombre_corto="Niños y Adolescentes", descripcion_detallada="Trabajar con niños y adolescentes"), 
            Preferencias(nombre_corto="Educación y formación", descripcion_detallada="Actividades educativas"), 
            Preferencias(nombre_corto="Ambiente y sostenibilidad", descripcion_detallada="Actividades ambientales"), 
            Preferencias(nombre_corto="Deporte y recreación", descripcion_detallada="Actividades deportivas") 
        ]
        db.session.add_all(preferencias)

    # Crea facilidades para actividades
    if Facilidad.query.count() == 0: 
        facilidades = [ 
            Facilidad(nombre_facilidad="Rampas", descripcion="Acceso con rampas para sillas de ruedas"), 
            Facilidad(nombre_facilidad="Intérpretes", descripcion="Intérpretes de lengua de señas disponibles"), 
            Facilidad(nombre_facilidad="Material braille", descripcion="Material disponible en sistema braille"), 
            Facilidad(nombre_facilidad="Materiales en audio", descripcion="Material accesible en audio"), 
            Facilidad(nombre_facilidad="Otros", descripcion="Otros o ninguno") 
        ]
        db.session.add_all(facilidades)

    # Crea usuarios
    if Usuarios.query.count() == 0:
        org1 = Organizaciones.query.filter_by(id_organizacion=1).first()
        org2 = Organizaciones.query.filter_by(id_organizacion=2).first()

        usuarios_data = [
            # Administrador
            {"DNI":"12345678", "nombre":"Dany", "apellido":"Palomino", "email":"admin@konectai.com", "password":"Hashed12", "celular":"987654321", "direccion":"Av. Principal 123", "fecha_nacimiento":date(1980, 5, 15), "genero":"masculino", "perfil":"administrador", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            # Organizador 1
            {"DNI":"87654321", "nombre":"Ana", "apellido":"García", "email":"ana.garcia@inclusionperu.org", "password":"Hashed87", "celular":"912345678", "direccion":"Calle Secundaria 456", "fecha_nacimiento":date(1992, 8, 20), "genero":"femenino", "perfil":"organizador", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz), "org_instance": org1},
            # Organizador 2
            {"DNI":"78223344", "nombre":"Carlos", "apellido":"Lopez", "email":"carlos.lopez@manossolidarias.org", "password":"Hashed78", "celular":"923456789", "direccion":"Av. Libertad 789", "fecha_nacimiento":date(1985, 3, 10), "genero":"masculino", "perfil":"organizador", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz), "org_instance": org2},
            # Voluntarios
            {"DNI":"44556677", "nombre":"Elena", "apellido":"Rojas", "email":"elena@email.com", "password":"Hashed44", "celular":"987654334", "direccion":"Jr. Cusco 3031", "fecha_nacimiento":date(1988, 4, 27), "genero":"femenino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"55667788", "nombre":"Javier", "apellido":"Paredes", "email":"javier.paredes@example.com", "password":"Hashed55", "celular":"998877665", "direccion":"Calle Los Pinos 450", "fecha_nacimiento":date(1995, 11, 5), "genero":"masculino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"66778899", "nombre":"Sofia", "apellido":"Castro", "email":"sofia.castro@example.com", "password":"Hashed66", "celular":"911223344", "direccion":"Av. El Sol 987", "fecha_nacimiento":date(2000, 7, 12), "genero":"femenino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"77889900", "nombre":"Luis", "apellido":"Mendoza", "email":"luis.mendoza@example.com", "password":"Hashed77", "celular":"933445566", "direccion":"Jr. Las Palmeras 123", "fecha_nacimiento":date(1998, 1, 25), "genero":"masculino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"88990011", "nombre":"Carmen", "apellido":"Diaz", "email":"carmen.diaz@example.com", "password":"Hashed88", "celular":"944556677", "direccion":"Calle Las Begonias 789", "fecha_nacimiento":date(1993, 9, 30), "genero":"femenino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"99001122", "nombre":"Pedro", "apellido":"Vargas", "email":"pedro.vargas@example.com", "password":"Hashed99", "celular":"955667788", "direccion":"Av. Los Incas 321", "fecha_nacimiento":date(1996, 6, 18), "genero":"masculino", "perfil":"voluntario", "estado_usuario":"activo", "fecha_registro":datetime.now(peru_tz)},
            {"DNI":"00112233", "nombre":"Rosa", "apellido":"Chavez", "email":"rosa.chavez@example.com", "password":"Hashed00", "celular":"966778899", "direccion":"Jr. Union 654", "fecha_nacimiento":date(1991, 12, 3), "genero":"femenino", "perfil":"voluntario", "estado_usuario":"inactivo", "fecha_registro":datetime.now(peru_tz)}
        ]

        for data in usuarios_data:
            password = data.pop("password")
            org_instance = data.pop("org_instance", None)
            usuario = Usuarios(**data)
            usuario.set_password(password)
            if org_instance and usuario.perfil == 'organizador':
                usuario.organizaciones.append(org_instance)
            db.session.add(usuario)
        db.session.commit()

        # Fetching users and discapacidades to be sure
        user_elena = Usuarios.query.filter_by(email="elena@email.com").first()
        user_javier = Usuarios.query.filter_by(email="javier.paredes@example.com").first()
        user_sofia = Usuarios.query.filter_by(email="sofia.castro@example.com").first()
        user_luis = Usuarios.query.filter_by(email="luis.mendoza@example.com").first()
        user_carmen = Usuarios.query.filter_by(email="carmen.diaz@example.com").first()
        user_pedro = Usuarios.query.filter_by(email="pedro.vargas@example.com").first()
        user_rosa = Usuarios.query.filter_by(email="rosa.chavez@example.com").first()

        disc_auditiva = Discapacidades.query.filter_by(nombre="Auditiva").first()
        disc_visual = Discapacidades.query.filter_by(nombre="Visual").first()
        disc_motriz = Discapacidades.query.filter_by(nombre="Motriz").first()

        if user_elena and disc_auditiva:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_elena.id_usuario, id_discapacidad=disc_auditiva.id_discapacidad, gravedad="moderada", apoyo_requerido="interprete"))
        if user_javier and disc_auditiva:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_javier.id_usuario, id_discapacidad=disc_auditiva.id_discapacidad, gravedad="leve", apoyo_requerido="otros"))
        if user_sofia and disc_auditiva:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_sofia.id_usuario, id_discapacidad=disc_auditiva.id_discapacidad, gravedad="grave", apoyo_requerido="interprete"))
        if user_luis and disc_visual:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_luis.id_usuario, id_discapacidad=disc_visual.id_discapacidad, gravedad="moderada", apoyo_requerido="otros"))
        if user_carmen and disc_visual:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_carmen.id_usuario, id_discapacidad=disc_visual.id_discapacidad, gravedad="leve", apoyo_requerido="otros"))
        if user_pedro and disc_motriz:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_pedro.id_usuario, id_discapacidad=disc_motriz.id_discapacidad, gravedad="grave", apoyo_requerido="otros"))
        if user_rosa and disc_motriz:
            db.session.add(UsuarioDiscapacidad(id_usuario=user_rosa.id_usuario, id_discapacidad=disc_motriz.id_discapacidad, gravedad="moderada", apoyo_requerido="otros"))

        # Asignar preferencias a usuarios
        user_ana = Usuarios.query.filter_by(email="ana.garcia@inclusionperu.org").first()
        user_carlos = Usuarios.query.filter_by(email="carlos.lopez@manossolidarias.org").first()
        # IDs for pref: 1:Niños, 2:Educación, 3:Ambiente, 4:Deporte
        pref_ninos = Preferencias.query.filter_by(nombre_corto="Niños y Adolescentes").first()
        pref_edu = Preferencias.query.filter_by(nombre_corto="Educación y formación").first()
        pref_ambiente = Preferencias.query.filter_by(nombre_corto="Ambiente y sostenibilidad").first()
        pref_deporte = Preferencias.query.filter_by(nombre_corto="Deporte y recreación").first()

        if user_ana and pref_ninos: user_ana.preferencias.append(pref_ninos)
        if user_ana and pref_edu: user_ana.preferencias.append(pref_edu)
        if user_carlos and pref_ambiente: user_carlos.preferencias.append(pref_ambiente)
        if user_carlos and pref_deporte: user_carlos.preferencias.append(pref_deporte)
        if user_elena and pref_ninos: user_elena.preferencias.append(pref_ninos)
        if user_elena and pref_deporte: user_elena.preferencias.append(pref_deporte)
        if user_javier and pref_edu: user_javier.preferencias.append(pref_edu)
        if user_sofia and pref_ambiente: user_sofia.preferencias.append(pref_ambiente)
        if user_luis and pref_ninos: user_luis.preferencias.append(pref_ninos)
        if user_carmen and pref_deporte: user_carmen.preferencias.append(pref_deporte)
        if user_pedro and pref_deporte: user_pedro.preferencias.append(pref_deporte)
        if user_rosa and pref_edu: user_rosa.preferencias.append(pref_edu)

    # Crear actividades
    if Actividades.query.count() == 0:
        org1 = Organizaciones.query.filter_by(id_organizacion=1).first()
        org2 = Organizaciones.query.filter_by(id_organizacion=2).first()
        org3 = Organizaciones.query.filter_by(id_organizacion=3).first()
        org4 = Organizaciones.query.filter_by(id_organizacion=4).first()

        facilidad_rampas = Facilidad.query.filter_by(nombre_facilidad="Rampas").first()
        facilidad_interpretes = Facilidad.query.filter_by(nombre_facilidad="Intérpretes").first()
        facilidad_braille = Facilidad.query.filter_by(nombre_facilidad="Material braille").first()

        actividades_data = [
            {
                "nombre":"Taller de lectura inclusiva", "descripcion":"Taller de lectura para personas con discapacidad visual",
                "fecha_actividad":datetime(2025, 1, 15, 10, 0), "ubicacion":"Biblioteca Nacional, Lima", "tipo":"presencial",
                "habilidades_requeridas":"Paciencia, conocimiento básico de braille", "es_inclusiva":True, "cupo_maximo":20,
                "estado":"abierto", "imagen":"lectura_inclusiva.jpg", "compatibilidad":"95.00", "etiqueta":"educación",
                "organizacion_instance":org1, "facilidades_instances": [facilidad_braille] if facilidad_braille else []
            },
            {
                "nombre":"Clases de lengua de señas", "descripcion":"Curso básico de lengua de señas peruana",
                "fecha_actividad":datetime(2025, 2, 1, 18, 0), "ubicacion":"Online", "tipo":"virtual",
                "habilidades_requeridas":"Ninguna", "es_inclusiva":True, "cupo_maximo":30, "estado":"abierto",
                "imagen":"ninguno.jpg", "compatibilidad":"90.00", "etiqueta":"educación",
                "organizacion_instance":org1, "facilidades_instances": [facilidad_interpretes] if facilidad_interpretes else []
            },
            {
                "nombre":"Campaña de reforestación en Lomas de Lúcumo", "descripcion":"Jornada de plantación de árboles nativos y limpieza de senderos.",
                "fecha_actividad":datetime(2025, 3, 22, 9, 0), "ubicacion":"Lomas de Lúcumo, Pachacamac, Lima", "tipo":"presencial",
                "habilidades_requeridas":"Resistencia física básica, amor por la naturaleza.", "es_inclusiva":False, "cupo_maximo":50,
                "estado":"abierto", "imagen":"reforestacion_accesible.jpg", "compatibilidad":"75.00", "etiqueta":"ambiente y sostenibilidad",
                "organizacion_instance":org3, "facilidades_instances": [facilidad_rampas] if facilidad_rampas else []
            },
            {
                "nombre":"Apoyo psicológico con señas a adolescentes", "descripcion":"Apoyo emocional a adolescentes en riesgo",
                "fecha_actividad":datetime(2025, 3, 12, 10, 0), "ubicacion":"Huancayo, Perú", "tipo":"virtual",
                "habilidades_requeridas":"conocimiento de señas", "es_inclusiva":True, "cupo_maximo":26, "estado":"abierto",
                "imagen":"ninguno.jpg", "compatibilidad":"87.00", "etiqueta":"niños y adolescentes",
                "organizacion_instance":org4, "facilidades_instances": [facilidad_interpretes] if facilidad_interpretes else []
            },
            {
                "nombre":"Taller de dibujo para niños con discapacidad", "descripcion":"Sesiones de arte inclusivo para niños",
                "fecha_actividad":datetime(2025, 7, 1, 15, 0), "ubicacion":"Huancayo, Perú", "tipo":"presencial",
                "habilidades_requeridas":"conocimiento de señas", "es_inclusiva":True, "cupo_maximo":15, "estado":"abierto",
                "imagen":"arte_urbano.jpg", "compatibilidad":"87.00", "etiqueta":"niños y adolescentes",
                "organizacion_instance":org2, "facilidades_instances": [facilidad_interpretes] if facilidad_interpretes else []
            },
            {
                "nombre":"Campaña de Limpieza Costera", "descripcion":"Recojo de residuos sólidos para proteger el ecosistema marino",
                "fecha_actividad":datetime(2025, 6, 10, 9, 0), "ubicacion":"Lima, Perú", "tipo":"presencial",
                "habilidades_requeridas":"amor por la naturaleza", "es_inclusiva":True, "cupo_maximo":15, "estado":"abierto",
                "imagen":"limpieza_costera.jpg", "compatibilidad":"87.00", "etiqueta":"Ambiente y sostenibilidad",
                "organizacion_instance":org1, "facilidades_instances": [facilidad_interpretes] if facilidad_interpretes else []
            },
            {
                "nombre":"Tutorías Escolares en Zonas Rurales", "descripcion":"Reforzamiento escolar en comunidades rurales",
                "fecha_actividad":datetime(2025, 8, 5, 18, 0), "ubicacion":"Huancayo, Perú", "tipo":"presencial",
                "habilidades_requeridas":"docente de nivel primario", "es_inclusiva":False, "cupo_maximo":3, "estado":"abierto",
                "imagen":"tutorias_rurales.jpg", "compatibilidad":"87.00", "etiqueta":"Educación y formación",
                "organizacion_instance":org3, "facilidades_instances": [facilidad_interpretes] if facilidad_interpretes else []
            },
            {
                "nombre":"Jornada deportiva inclusiva", "descripcion":"Actividades deportivas inclusivas para voluntarios",
                "fecha_actividad":datetime(2025, 9, 3, 9, 0), "ubicacion":"Huancayo, Perú", "tipo":"presencial",
                "habilidades_requeridas":"Resistencia física básica", "es_inclusiva":True, "cupo_maximo":10, "estado":"abierto",
                "imagen":"festival_deportivo.jpg", "compatibilidad":"87.00", "etiqueta":"Deporte y recreación",
                "organizacion_instance":org2, "facilidades_instances": [facilidad_rampas] if facilidad_rampas else []
            }            
        ]
        for data in actividades_data:
            org_instance = data.pop("organizacion_instance", None)
            facilidades_instances = data.pop("facilidades_instances", [])
            actividad = Actividades(**data)
            if org_instance:
                actividad.organizacion = org_instance
            if facilidades_instances:
                for fac in facilidades_instances:
                    actividad.facilidades.append(fac)
            db.session.add(actividad)

    # Crear inscripciones
    if Inscripciones.query.count() == 0:
        # voluntarios especificos
        user_elena = Usuarios.query.filter_by(email="elena@email.com").first()
        user_javier = Usuarios.query.filter_by(email="javier.paredes@example.com").first()
        user_sofia = Usuarios.query.filter_by(email="sofia.castro@example.com").first()
        user_luis = Usuarios.query.filter_by(email="luis.mendoza@example.com").first()
        user_carmen = Usuarios.query.filter_by(email="carmen.diaz@example.com").first()
        user_pedro = Usuarios.query.filter_by(email="pedro.vargas@example.com").first()
        # actividades especificas
        act_lectura = Actividades.query.filter_by(nombre="Taller de lectura inclusiva").first()
        act_senas = Actividades.query.filter_by(nombre="Clases de lengua de señas").first()
        act_reforestacion = Actividades.query.filter_by(nombre="Campaña de reforestación en Lomas de Lúcumo").first()
        act_apoyo_psico = Actividades.query.filter_by(nombre="Apoyo psicológico con señas a adolescentes").first()
        act_dibujo = Actividades.query.filter_by(nombre="Taller de dibujo para niños con discapacidad").first()
        act_limpieza = Actividades.query.filter_by(nombre="Campaña de Limpieza Costera").first()
        act_tutorias = Actividades.query.filter_by(nombre="Tutorías Escolares en Zonas Rurales").first()
        act_deportiva = Actividades.query.filter_by(nombre="Jornada deportiva inclusiva").first()

        predefined_inscriptions = []
        if user_elena and act_lectura: predefined_inscriptions.append({'user': user_elena, 'activity': act_lectura})
        if user_elena and act_senas: predefined_inscriptions.append({'user': user_elena, 'activity': act_senas})        
        if user_javier and act_reforestacion: predefined_inscriptions.append({'user': user_javier, 'activity': act_reforestacion})        
        if user_sofia and act_apoyo_psico: predefined_inscriptions.append({'user': user_sofia, 'activity': act_apoyo_psico})
        if user_sofia and act_dibujo: predefined_inscriptions.append({'user': user_sofia, 'activity': act_dibujo})
        if user_sofia and act_limpieza: predefined_inscriptions.append({'user': user_sofia, 'activity': act_limpieza})
        if user_luis and act_tutorias: predefined_inscriptions.append({'user': user_luis, 'activity': act_tutorias})
        if user_luis and act_deportiva: predefined_inscriptions.append({'user': user_luis, 'activity': act_deportiva})
        if user_carmen and act_lectura: predefined_inscriptions.append({'user': user_carmen, 'activity': act_lectura})
        if user_carmen and act_reforestacion: predefined_inscriptions.append({'user': user_carmen, 'activity': act_reforestacion})
        if user_pedro and act_senas: predefined_inscriptions.append({'user': user_pedro, 'activity': act_senas})
        if user_pedro and act_apoyo_psico: predefined_inscriptions.append({'user': user_pedro, 'activity': act_apoyo_psico})

        if predefined_inscriptions:
            for item in predefined_inscriptions:
                user = item['user']
                activity = item['activity']
                
                # revisa duplicados
                existe_inscripcion = Inscripciones.query.filter_by(
                    id_usuario=user.id_usuario,
                    id_actividad=activity.id_actividad
                ).first()
                
                if not existe_inscripcion:
                    inscripcion = Inscripciones(
                        id_usuario=user.id_usuario,
                        id_actividad=activity.id_actividad,
                        fecha_inscripcion=datetime.now(peru_tz),
                        estado_inscripcion='confirmada' 
                    )
                    db.session.add(inscripcion)
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error al agregar inscripciones iniciales: {e}")
        else:
            print("No se pudieron agregar inscripciones predefinidas")
    # Guardar Commit
    db.session.commit()
    print("Datos iniciales agregados a la base de datos.")
