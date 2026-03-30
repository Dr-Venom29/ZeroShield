FROM node:20-alpine

WORKDIR /app

COPY frontend/zeroshield-ui/package*.json ./
RUN npm install

COPY frontend/zeroshield-ui ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
