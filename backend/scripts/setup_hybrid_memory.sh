#!/bin/bash

# Script to set up the hybrid memory system and migrate data

# Color codes for pretty output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to display step headers
show_step() {
    echo
    echo -e "${BOLD}${GREEN}=== $1 ===${NC}"
    echo
}

# Function to check for required environment variables
check_env_variables() {
    show_step "Checking environment variables"
    
    local missing=0
    local required_vars=(
        "SUPABASE_URL"
        "SUPABASE_ANON_KEY"
        "SUPABASE_SERVICE_ROLE_KEY"
        "QDRANT_URL"
        "QDRANT_API_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${YELLOW}Warning: $var is not set in .env file${NC}"
            missing=$((missing+1))
        else
            echo -e "${GREEN}✓${NC} $var is set"
        fi
    done
    
    if [ $missing -gt 0 ]; then
        echo
        echo -e "${YELLOW}Some required environment variables are missing.${NC}"
        read -p "Would you like to update your .env file now? (y/n): " update_env
        
        if [[ $update_env == "y" || $update_env == "Y" ]]; then
            update_env_file
        else
            echo -e "${YELLOW}Please make sure to update your .env file manually before proceeding.${NC}"
        fi
    else
        echo -e "${GREEN}All required environment variables are set!${NC}"
    fi
}

# Function to update .env file
update_env_file() {
    show_step "Updating .env file"
    
    local env_file=".env"
    
    # Make a backup of the current .env file
    if [ -f "$env_file" ]; then
        cp "$env_file" "${env_file}.backup"
        echo -e "${GREEN}Created backup of current .env file at ${env_file}.backup${NC}"
    fi
    
    echo "DATABASE_PROVIDER=hybrid" > "$env_file"
    echo "VECTOR_PROVIDER=qdrant" >> "$env_file"
    echo >> "$env_file"
    
    # Supabase configuration
    echo "# Supabase settings" >> "$env_file"
    read -p "Enter your Supabase URL: " supabase_url
    echo "SUPABASE_URL=$supabase_url" >> "$env_file"
    
    read -p "Enter your Supabase Anon Key: " supabase_anon_key
    echo "SUPABASE_ANON_KEY=$supabase_anon_key" >> "$env_file"
    
    read -p "Enter your Supabase Service Role Key: " supabase_service_key
    echo "SUPABASE_SERVICE_ROLE_KEY=$supabase_service_key" >> "$env_file"
    
    echo >> "$env_file"
    echo "# PostgreSQL Settings (for Supabase)" >> "$env_file"
    echo "POSTGRES_HOST=$(echo $supabase_url | sed 's|https://||' | sed 's|.supabase.co||').supabase.co" >> "$env_file"
    echo "POSTGRES_PORT=5432" >> "$env_file"
    echo "POSTGRES_DB=postgres" >> "$env_file"
    read -p "Enter your PostgreSQL username: " postgres_user
    echo "POSTGRES_USER=$postgres_user" >> "$env_file"
    read -p "Enter your PostgreSQL password: " postgres_password
    echo "POSTGRES_PASSWORD=$postgres_password" >> "$env_file"
    echo "POSTGRES_SSL=require" >> "$env_file"
    
    echo >> "$env_file"
    echo "# Qdrant Cloud Settings" >> "$env_file"
    read -p "Enter your Qdrant Cloud URL: " qdrant_url
    echo "QDRANT_URL=$qdrant_url" >> "$env_file"
    
    read -p "Enter your Qdrant API Key: " qdrant_api_key
    echo "QDRANT_API_KEY=$qdrant_api_key" >> "$env_file"
    
    read -p "Enter your Qdrant collection name (default: gitmesh_memory): " qdrant_collection
    qdrant_collection=${qdrant_collection:-gitmesh_memory}
    echo "QDRANT_COLLECTION_NAME=$qdrant_collection" >> "$env_file"
    
    echo -e "${GREEN}.env file has been updated successfully!${NC}"
}

# Function to install dependencies
install_dependencies() {
    show_step "Installing dependencies"
    
    echo "Installing required packages..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Dependencies installed successfully!${NC}"
    else
        echo -e "${RED}Error installing dependencies. Please check the error messages above.${NC}"
        exit 1
    fi
}

# Function to run the migration script
run_migration() {
    show_step "Running data migration"
    
    echo "This will migrate your existing data to the hybrid storage system."
    read -p "Continue with migration? (y/n): " confirm_migration
    
    if [[ $confirm_migration == "y" || $confirm_migration == "Y" ]]; then
        echo "Running migration script..."
        python scripts/migrate_supabase_to_qdrant.py
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Migration completed successfully!${NC}"
        else
            echo -e "${RED}Error during migration. Please check the error messages above.${NC}"
        fi
    else
        echo "Migration skipped."
    fi
}

# Function to test the setup
test_setup() {
    show_step "Testing hybrid memory system"
    
    echo "Running test script to verify the setup..."
    python scripts/test_hybrid_memory.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Setup test passed successfully!${NC}"
    else
        echo -e "${RED}Setup test failed. Please check the error messages above.${NC}"
    fi
}

# Main execution
echo -e "${BOLD}${GREEN}Hybrid Memory System Setup${NC}"
echo -e "This script will help you set up the hybrid memory system using Qdrant Cloud and Supabase."
echo

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python is not installed or not in PATH.${NC}"
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is not installed or not in PATH.${NC}"
    exit 1
fi

# Menu
PS3="Select an option: "
options=("Check/Update Environment Variables" "Install Dependencies" "Run Migration" "Test Setup" "Exit")

select opt in "${options[@]}"
do
    case $opt in
        "Check/Update Environment Variables")
            check_env_variables
            ;;
        "Install Dependencies")
            install_dependencies
            ;;
        "Run Migration")
            run_migration
            ;;
        "Test Setup")
            test_setup
            ;;
        "Exit")
            echo -e "${GREEN}Goodbye!${NC}"
            break
            ;;
        *) 
            echo "Invalid option $REPLY"
            ;;
    esac
    
    # Show menu again after action completes
    echo
    echo -e "${YELLOW}What would you like to do next?${NC}"
done

exit 0
