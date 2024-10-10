// Define main function (script entry)

function main(config) {

  const newRules = [
    "IP-CIDR,你的服务器公网IP/24,DIRECT"
  ];

  if (!config.rules) {
    config.rules = [];
  }

  config.rules.unshift(...newRules);

  return config;
}