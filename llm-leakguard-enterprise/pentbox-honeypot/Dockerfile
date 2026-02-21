FROM kalilinux/kali-rolling:latest

RUN apt-get update && apt-get install -y \
    ruby-full ruby-dev git wget tar netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /pentbox

RUN git clone https://github.com/technicaldada/pentbox.git . && \
    find . -name "pentbox.rb" -exec chmod +x {} \; || \
    (cd pentbox-1.8 && chmod +x pentbox.rb 2>/dev/null || true)

COPY honeypot-start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 23
CMD ["/start.sh"]
