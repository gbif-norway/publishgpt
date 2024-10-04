#!/bin/bash
set +e  # Continue on errors

COLOR_BLUE="\033[0;94m"
COLOR_GREEN="\033[0;92m"
COLOR_RESET="\033[0m"

# Print useful output for user
echo -e "${COLOR_BLUE}
     %########%
     %###########%       ____                 _____
         %#########%    |  _ \   ___ __   __ / ___/  ____    ____   ____ ___
         %#########%    | | | | / _ \\\\\ \ / / \___ \ |  _ \  / _  | / __// _ \\
     %#############%    | |_| |(  __/ \ V /  ____) )| |_) )( (_| |( (__(  __/
     %#############%    |____/  \___|  \_/   \____/ |  __/  \__,_| \___\\\\\___|
 %###############%                                  |_|
 %###########%${COLOR_RESET}


Welcome to your development container!

This is how you can work with it:
- Files will be synchronized between your local machine and this container
- Some ports will be forwarded, so you can access this container via localhost
- Run \`${COLOR_GREEN}python main.py${COLOR_RESET}\` to start the application
"

# Set terminal prompt
export PS1="\[${COLOR_BLUE}\]devspace\[${COLOR_RESET}\] ./\W \[${COLOR_BLUE}\]\\$\[${COLOR_RESET}\] "
if [ -z "$BASH" ]; then export PS1="$ "; fi

# Include project's bin/ folder in PATH
export PATH="./bin:$PATH"

# Install PostgreSQL client quietly if not already installed
if ! command -v psql &> /dev/null
then
    echo -e "${COLOR_GREEN}Installing PostgreSQL client...${COLOR_RESET}"
    sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql-client > /dev/null 2>&1
    echo -e "${COLOR_GREEN}PostgreSQL client installed successfully.${COLOR_RESET}"
else
    echo -e "${COLOR_GREEN}PostgreSQL client is already installed.${COLOR_RESET}"
fi

# Define a function to start the application using Django's development server
start_app() {
    python manage.py runserver 0.0.0.0:8000
}

echo -e "${COLOR_GREEN}Defining function 'start_app' to run Django development server...${COLOR_RESET}"
echo -e "${COLOR_GREEN}You can now start the application by running 'start_app'${COLOR_RESET}"

# Define an alias function to connect to the database using psql
connect_db() {
    PGPASSWORD=$SQL_PASSWORD psql -h $SQL_HOST -p $SQL_PORT -U $SQL_USER -d $SQL_DATABASE
}

echo -e "${COLOR_GREEN}Defining function 'connect_db' to connect to the database using psql...${COLOR_RESET}"
echo -e "${COLOR_GREEN}You can now connect to the database by running 'connect_db'${COLOR_RESET}"

# Export the functions so they're available in child shells
export -f start_app
export -f connect_db

# Open shell
bash --norc
