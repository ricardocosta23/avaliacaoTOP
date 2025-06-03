import logging
import json
import requests
import uuid
from datetime import datetime
from flask import request, render_template, redirect, url_for, jsonify, flash
from app import app

# Monday.com API configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjQxMDM1MDMyNiwiYWFpIjoxMSwidWlkIjo1NTIyMDQ0LCJpYWQiOiIyMDI0LTA5LTEzVDExOjUyOjQzLjAwMFoiLCJwZXIiOiJtZTp3cml0ZSIsImFjdGlkIjozNzk1MywicmduIjoidXNlMSJ9.hwTlwMwtbhKdZsYcGT7UoENBLZUAxnfUXchj5RZJBz4"
BOARD_ID = "9241811459"

# In-memory storage for survey data (temporary until submitted to Monday.com)
surveys = {}

def format_date_portuguese(date_str):
    """Format date string to Portuguese format (e.g., 'Maio de 2025')"""
    months_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    
    try:
        # Try different date formats that might come from Monday.com
        for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                date_obj = datetime.strptime(date_str, date_format)
                month_name = months_pt.get(date_obj.month, "")
                return f"{month_name} de {date_obj.year}"
            except ValueError:
                continue
        
        # If none of the formats work, try to extract year and month from string
        import re
        
        # Look for YYYY-MM pattern
        match = re.search(r'(\d{4})-(\d{1,2})', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            month_name = months_pt.get(month, "")
            return f"{month_name} de {year}"
        
        # Look for MM/YYYY or MM-YYYY pattern
        match = re.search(r'(\d{1,2})[/-](\d{4})', date_str)
        if match:
            month = int(match.group(1))
            year = int(match.group(2))
            month_name = months_pt.get(month, "")
            return f"{month_name} de {year}"
            
        return date_str  # Return original if can't parse
        
    except Exception as e:
        print(f"Error formatting date '{date_str}': {e}")
        return date_str

def monday_graphql_request(query, variables=None):
    """Make a GraphQL request to Monday.com API"""
    headers = {
        "Authorization": f"Bearer {MONDAY_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "variables": variables or {}
    }

    response = requests.post(MONDAY_API_URL, json=payload, headers=headers)
    return response.json()

def get_item_data(item_id):
    """Fetch item data including Date and Location columns"""
    query = """
    query($itemId: [ID!]) {
        items(ids: $itemId) {
            id
            name
            column_values {
                id
                text
                value
                ... on MirrorValue {
                    display_value
                }
            }
        }
    }
    """

    variables = {
        "itemId": [str(item_id)]
    }

    result = monday_graphql_request(query, variables)
    return result

def update_survey_link(item_id, survey_url):
    """Update the link column with survey URL"""
    query = """
    mutation($itemId: ID!, $boardId: ID!, $columnId: String!, $value: JSON!) {
        change_column_value(
            item_id: $itemId, 
            board_id: $boardId, 
            column_id: $columnId, 
            value: $value
        ) {
            id
        }
    }
    """

    variables = {
        "itemId": str(item_id),
        "boardId": BOARD_ID,
        "columnId": "text_mkrb8f7",
        "value": f'"{survey_url}"'
    }

    result = monday_graphql_request(query, variables)
    return result

def create_survey_result_item(survey_data):
    """Create a new item with survey results"""
    query = """
    mutation($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
        create_item(
            board_id: $boardId,
            item_name: $itemName,
            column_values: $columnValues
        ) {
            id
            name
        }
    }
    """

    # Build column values with all survey data using correct Monday.com column IDs
    column_values = {}

    # Original Monday.com data
    if survey_data.get('company_name'):
        column_values["text_mkrjdnry"] = survey_data['company_name']
    
    if survey_data.get('location'):
        column_values["text_mkrb17ct"] = survey_data['location']
    
    if survey_data.get('original_date'):
        column_values["date_mkrjxb5d"] = survey_data['original_date']
    
    if survey_data.get('board_relation_value'):
        column_values["text_mkrb96zz"] = survey_data['board_relation_value']

    # Aérea (Sim ou Não) - only send if "sim"
    if survey_data.get('used_air_travel') == 'sim':
        column_values["dropdown_mkrj4m2n"] = 'sim'

    # Nota aéreo
    if survey_data.get('air_rating'):
        column_values["numeric_mkrjqam"] = str(survey_data['air_rating'])

    # Hotel 1 name and rating
    if survey_data.get('hotel_1_name'):
        column_values["text_mkrjf13y"] = survey_data['hotel_1_name']
    if survey_data.get('hotel_1_rating'):
        column_values["numeric_mkrjpfxv"] = str(survey_data['hotel_1_rating'])

    # Hotel 2 name and rating
    if survey_data.get('hotel_2_name'):
        column_values["text_mkrjk4yg"] = survey_data['hotel_2_name']
    if survey_data.get('hotel_2_rating'):
        column_values["numeric_mkrjg1ar"] = str(survey_data['hotel_2_rating'])

    # Guias rating
    if survey_data.get('guides_rating'):
        column_values["numeric_mkrj330c"] = str(survey_data['guides_rating'])

    # Restaurantes (Sim ou Não) - only send if "sim"
    if survey_data.get('had_restaurants') == 'sim':
        column_values["dropdown_mkrj9c4s"] = 'sim'

    # Nota restaurantes
    if survey_data.get('restaurants_rating'):
        column_values["numeric_mkrjp7f9"] = str(survey_data['restaurants_rating'])

    # Passeios e atividades (Sim ou Não) - only send if "sim"
    if survey_data.get('had_activities') == 'sim':
        column_values["dropdown_mkrjp8cd"] = 'sim'

    # Nota Passeios e atividades
    if survey_data.get('activities_rating'):
        column_values["numeric_mkrj6132"] = str(survey_data['activities_rating'])

    # Nota Viagem de forma geral
    if survey_data.get('overall_rating'):
        column_values["numeric_mkrjv5re"] = str(survey_data['overall_rating'])

    # Comentários
    if survey_data.get('comments'):
        column_values["long_text_mkrjwfwx"] = survey_data['comments']

    # Sugestão de Destino
    if survey_data.get('next_destination'):
        column_values["long_text_mkrjd4z0"] = survey_data['next_destination']

    # Use trip name as item name
    item_name = survey_data.get('trip_name', 'Nova avaliação')
    
    variables = {
        "boardId": "9242892489",
        "itemName": item_name,
        "columnValues": json.dumps(column_values)
    }

    result = monday_graphql_request(query, variables)
    return result

@app.route('/webhook/monday', methods=['GET', 'POST'])
def monday_webhook():
    """Handle Monday.com webhook with challenge response"""

    # Log all incoming requests
    logging.info(f"Webhook received - Method: {request.method}")
    logging.info(f"Headers: {dict(request.headers)}")

    if request.method == 'GET':
        # Handle challenge verification
        challenge = request.args.get('challenge')
        if challenge:
            logging.info(f"GET challenge received: {challenge}")
            return challenge, 200, {'Content-Type': 'text/plain'}
        logging.info("GET request without challenge - endpoint ready")
        return "Webhook endpoint ready", 200

    elif request.method == 'POST':
        try:
            # Parse webhook data
            data = request.get_json()
            logging.info(f"Webhook data received: {data}")

            # Log raw request data for debugging
            raw_data = request.get_data(as_text=True)
            logging.info(f"Raw request data: {raw_data}")

            # Handle challenge response for POST requests
            if data and 'challenge' in data:
                challenge = data['challenge']
                print("Received POST challenge:", challenge)
                logging.info(f"POST challenge received: {challenge}")
                return jsonify({'challenge': challenge}), 200

            # Extract basic info from webhook
            event_data = data.get('event', {})
            pulse_id = event_data.get('pulseId')
            trip_name = event_data.get('pulseName', 'Unknown Trip')

            if not pulse_id:
                return jsonify({"error": "No pulse ID found"}), 400

            # Fetch complete item data using GraphQL
            print(f"Fetching data for item ID: {pulse_id}")
            item_data_response = get_item_data(pulse_id)

            if 'errors' in item_data_response:
                print(f"GraphQL error: {item_data_response['errors']}")
                location = "Unknown Location"
                date = "Unknown Date"
                company_name = "Unknown Company"
            else:
                items = item_data_response.get('data', {}).get('items', [])
                if items:
                    item = items[0]
                    column_values = item.get('column_values', [])

                    # Extract location, date, and company name from specific columns
                    location = "Unknown Location"
                    date = "Unknown Date"
                    company_name = "Unknown Company"

                    # Initialize additional variables
                    hotel_1 = None
                    hotel_2 = None
                    has_guides = False
                    formatted_date = "Data não disponível"
                    original_date = None  # Store original date for Monday.com registration
                    board_relation_value = None  # Store board relation value

                    for col in column_values:
                        print(f"Column ID: {col['id']}, Text: {col.get('text')}, Value: {col.get('value')}")

                        if col['id'] == 'lookup_mkrjh91x':  # Destination column (mirror)
                            # Mirror columns use display_value field
                            display_value = col.get('display_value')
                            if display_value:
                                location = display_value
                            else:
                                # Fallback to text or value
                                location = col.get('text') or col.get('value') or "Unknown Location"
                            print(f"Destination mirror column display_value: {display_value}")
                        elif col['id'] == 'lookup_mkrjpdz0':  # Date mirror column
                            # Extract and format the date from mirror column
                            display_value = col.get('display_value')
                            if display_value:
                                formatted_date = format_date_portuguese(display_value)
                                original_date = display_value  # Store original date for Monday.com
                            else:
                                # Fallback to text or value
                                raw_date = col.get('text') or col.get('value')
                                if raw_date:
                                    formatted_date = format_date_portuguese(raw_date)
                                    original_date = raw_date
                            print(f"Date mirror column display_value: {display_value}, formatted: {formatted_date}")
                        elif col['id'] == 'data':  # Original date column (fallback)
                            if formatted_date == "Data não disponível":
                                date = col.get('text') or "Unknown Date"
                        elif col['id'] == 'lookup_mkrb9ns5':  # Mirror column lookup for company
                            # Mirror columns use display_value field
                            display_value = col.get('display_value')
                            if display_value:
                                company_name = display_value
                            else:
                                # Fallback to text or value
                                company_name = col.get('text') or col.get('value') or "Unknown Company"
                            print(f"Company mirror column display_value: {display_value}")
                        elif col['id'] == 'text_mkrj9z52':  # Hotel 1 column
                            hotel_1_text = col.get('text')
                            if hotel_1_text and hotel_1_text.strip():
                                hotel_1 = hotel_1_text.strip()
                            print(f"Hotel 1: {hotel_1}")
                        elif col['id'] == 'text_mkrjz0tf':  # Hotel 2 column
                            hotel_2_text = col.get('text')
                            if hotel_2_text and hotel_2_text.strip():
                                hotel_2 = hotel_2_text.strip()
                            print(f"Hotel 2: {hotel_2}")
                        elif col['id'] == 'color_mkrjt1p5':  # Guides column
                            guides_value = col.get('text')
                            has_guides = guides_value == "Sim"
                            print(f"Has guides: {has_guides} (value: {guides_value})")
                        elif col['id'] == 'board_relation_mkrbw0h7':  # Board relation column
                            board_relation_text = col.get('text')
                            if board_relation_text and board_relation_text.strip():
                                board_relation_value = board_relation_text.strip()
                            print(f"Board relation: {board_relation_value}")

                    # Use formatted date if available, otherwise fallback to original date
                    if formatted_date != "Data não disponível":
                        date = formatted_date
                    
                    print(f"Extracted - Location: {location}, Date: {date}, Company: {company_name}")
                    print(f"Hotels - Hotel 1: {hotel_1}, Hotel 2: {hotel_2}")
                    print(f"Has guides: {has_guides}")
                else:
                    print("No items found in GraphQL response")
                    location = "Unknown Location"
                    date = "Unknown Date"
                    company_name = "Unknown Company"

            # Generate unique survey ID
            survey_id = str(uuid.uuid4())

            # Store survey data in memory
            surveys[survey_id] = {
                'survey_id': survey_id,
                'location': location,
                'date': date,
                'trip_name': trip_name,
                'company_name': company_name,
                'pulse_id': pulse_id,
                'hotel_1': hotel_1,  # Hotel name from Monday.com
                'hotel_2': hotel_2,  # Hotel name from Monday.com (if not blank)
                'has_guides': has_guides,  # Whether to show guides section
                'original_date': original_date,  # Original date for Monday.com registration
                'board_relation_value': board_relation_value  # Board relation value
            }

            # Generate survey URL
            survey_url = url_for('survey_form', survey_id=survey_id, _external=True)

            # Update Monday.com with survey link
            print(f"Updating Monday.com item {pulse_id} with survey link: {survey_url}")
            logging.info(f"Attempting to update Monday.com item {pulse_id} with survey link")

            try:
                update_result = update_survey_link(pulse_id, survey_url)
                logging.info(f"Monday.com update response: {update_result}")

                if 'errors' in update_result:
                    print(f"Error updating Monday.com: {update_result['errors']}")
                    logging.error(f"Monday.com API error: {update_result['errors']}")
                else:
                    print("Successfully updated Monday.com with survey link")
                    logging.info("Successfully updated Monday.com with survey link")
            except Exception as api_error:
                print(f"Exception when calling Monday.com API: {str(api_error)}")
                logging.error(f"Exception when calling Monday.com API: {str(api_error)}")

            # Log the survey page link to console
            print(f"\n{'='*60}")
            print(f"NEW SURVEY CREATED!")
            print(f"Survey ID: {survey_id}")
            print(f"Location: {location}")
            print(f"Date: {date}")
            print(f"Trip Name: {trip_name}")
            print(f"Company Name: {company_name}")
            print(f"Survey URL: {survey_url}")
            print(f"Monday.com Item ID: {pulse_id}")
            print(f"{'='*60}\n")

            return jsonify({
                "status": "success",
                "survey_id": survey_id,
                "survey_url": survey_url
            }), 200

        except Exception as e:
            logging.error(f"Error processing webhook: {str(e)}")
            return jsonify({"error": "Failed to process webhook"}), 500

@app.route('/survey/<survey_id>')
def survey_form(survey_id):
    """Display the NPS survey form"""
    survey = surveys.get(survey_id)

    if not survey:
        return "Pesquisa não encontrada", 404

    return render_template('survey.html', survey=survey)

@app.route('/survey/<survey_id>/submit', methods=['POST'])
def submit_survey(survey_id):
    """Handle survey submission"""
    survey = surveys.get(survey_id)

    if not survey:
        return "Pesquisa não encontrada", 404

    try:
        # Get all form data
        overall_rating = request.form.get('overall_rating')
        overall_rating = int(overall_rating) if overall_rating else None

        # Get optional ratings and convert to int if not empty
        air_rating = request.form.get('air_rating')
        air_rating = int(air_rating) if air_rating and air_rating.strip() else None
        
        guides_rating = request.form.get('guides_rating')
        guides_rating = int(guides_rating) if guides_rating and guides_rating.strip() else None
        
        hotel_1_rating = request.form.get('hotel_1_rating')
        hotel_1_rating = int(hotel_1_rating) if hotel_1_rating and hotel_1_rating.strip() else None
        
        hotel_2_rating = request.form.get('hotel_2_rating')
        hotel_2_rating = int(hotel_2_rating) if hotel_2_rating and hotel_2_rating.strip() else None
        
        restaurants_rating = request.form.get('restaurants_rating')
        restaurants_rating = int(restaurants_rating) if restaurants_rating and restaurants_rating.strip() else None
        
        activities_rating = request.form.get('activities_rating')
        activities_rating = int(activities_rating) if activities_rating and activities_rating.strip() else None

        # Get text responses
        comments = request.form.get('comments', '').strip()
        next_destination = request.form.get('next_destination', '').strip()

        # Get yes/no responses
        used_air_travel = request.form.get('used_air_travel')
        had_guides = request.form.get('had_guides')
        had_restaurants = request.form.get('had_restaurants')
        had_activities = request.form.get('had_activities')

        # Validate overall rating (mandatory)
        if not overall_rating:
            flash("Por favor, avalie a viagem de forma geral.", "error")
            return redirect(url_for('survey_form', survey_id=survey_id))

        if overall_rating < 1 or overall_rating > 10:
            flash("Por favor, selecione uma avaliação válida entre 1 e 10.", "error")
            return redirect(url_for('survey_form', survey_id=survey_id))

        # Create new item in Monday.com with survey results
        print(f"Creating Monday.com item for survey results")
        print(f"Debug - Received ratings:")
        print(f"  Overall: {overall_rating}")
        print(f"  Air: {air_rating}")
        print(f"  Guides: {guides_rating}")
        print(f"  Hotel 1: {hotel_1_rating}")
        print(f"  Hotel 2: {hotel_2_rating}")
        print(f"  Restaurants: {restaurants_rating}")
        print(f"  Activities: {activities_rating}")
        survey_data = {
            'trip_name': survey['trip_name'],
            'location': survey['location'],
            'company_name': survey['company_name'],
            'original_date': survey.get('original_date'),
            'board_relation_value': survey.get('board_relation_value'),
            'overall_rating': overall_rating,
            'air_rating': air_rating,
            'guides_rating': guides_rating,
            'hotel_1_rating': hotel_1_rating,
            'hotel_2_rating': hotel_2_rating,
            'restaurants_rating': restaurants_rating,
            'activities_rating': activities_rating,
            'comments': comments,
            'next_destination': next_destination,
            'used_air_travel': used_air_travel,
            'had_guides': had_guides,
            'had_restaurants': had_restaurants,
            'had_activities': had_activities,
            'hotel_1_name': survey.get('hotel_1'),  # Hotel names from original Monday.com data
            'hotel_2_name': survey.get('hotel_2')
        }

        monday_result = create_survey_result_item(survey_data)

        if 'errors' in monday_result:
            print(f"Error creating Monday.com item: {monday_result['errors']}")
            flash("Erro ao salvar resposta. Tente novamente.", "error")
            return redirect(url_for('survey_form', survey_id=survey_id))
        else:
            created_item = monday_result.get('data', {}).get('create_item', {})
            print(f"Successfully created Monday.com item: {created_item.get('id')}")

        # Log completion to console
        print(f"\n{'='*60}")
        print(f"SURVEY COMPLETED!")
        print(f"Survey ID: {survey_id}")
        print(f"Trip: {survey['trip_name']}")
        print(f"Location: {survey['location']}")
        print(f"Overall Rating: {overall_rating}")
        if air_rating:
            print(f"Air Travel Rating: {air_rating}")
        if guides_rating:
            print(f"Guides Rating: {guides_rating}")
        if hotel_1_rating:
            print(f"Hotel 1 Rating: {hotel_1_rating}")
        if hotel_2_rating:
            print(f"Hotel 2 Rating: {hotel_2_rating}")
        if restaurants_rating:
            print(f"Restaurants Rating: {restaurants_rating}")
        if activities_rating:
            print(f"Activities Rating: {activities_rating}")
        print(f"Comments: {comments if comments else 'No comments provided'}")
        print(f"Next Destination: {next_destination if next_destination else 'No suggestion provided'}")
        print(f"{'='*60}\n")

        flash("Obrigado pelo seu feedback!", "success")
        return redirect(url_for('thank_you', survey_id=survey_id))

    except (ValueError, TypeError):
        flash("Por favor, selecione uma avaliação válida.", "error")
        return redirect(url_for('survey_form', survey_id=survey_id))
    except Exception as e:
        logging.error(f"Error submitting survey: {str(e)}")
        flash("Ocorreu um erro ao enviar sua resposta. Por favor, tente novamente.", "error")
        return redirect(url_for('survey_form', survey_id=survey_id))

@app.route('/survey/<survey_id>/thank-you')
def thank_you(survey_id):
    """Display thank you page"""
    survey = surveys.get(survey_id)

    if not survey:
        return "Pesquisa não encontrada", 404

    return render_template('thank_you.html', survey=survey)

@app.route('/')
def index():
    """Home page"""
    return """
    <html>
    <head>
        <title>Sistema de Pesquisa NPS de Viagem</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 50px;
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; opacity: 0.9; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌍 Sistema de Pesquisa NPS de Viagem</h1>
            <p>Endpoint webhook pronto para receber dados do Monday.com</p>
            <p>Pesquisas serão geradas automaticamente quando webhooks forem recebidos</p>
        </div>
    </body>
    </html>
    """

@app.errorhandler(404)
def not_found_error(error):
    return render_template('thank_you.html', survey=None, error="Página não encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('thank_you.html', survey=None, error="Erro interno do servidor"), 500