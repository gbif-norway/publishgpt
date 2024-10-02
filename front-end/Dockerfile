FROM node:latest
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
EXPOSE 3000
CMD ["npm", "start"]
# CMD ["tail", "-f", "/dev/null"]

# npm run dev
