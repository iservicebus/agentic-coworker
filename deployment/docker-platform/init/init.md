# Clean up
(1) docker compose down
(2) delete all the volumes

# Start
(1) docker compose up -d
(2) initiate IAM for Keycloak: in /integrator/iam, python keycloak.py
(3) create tables in /integrator/db: create_tables.sh 
(4) populate tenant, apps configuration in tables /integrator/db: insert_tables.sh
(5) register services, in /integrator/scripts:  register_services.sh
(6)create table index tables in /tool_index: create_tables.sh
(7) enqueue the tools in /tool_index: python producer.py --file services_backup.json
(8) ingest tools in /tool_index: python consumer.py -i