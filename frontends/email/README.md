# cecibot-email

## `identifier` CHANGELOG

### v1

```python
{
    "identifier_version": 1,
    "identifier": {
        "headers": mail.headers  # type: Dict[str, str]
    }
}
```

## redis

### Key Scheme

- `email.rate_limiting.counter.complete.(<REVERSE DOMAIN>).(<EMAIL LOCAL>)`

   for whitelisted e-mail providers.
   
   __For instance:__

       email.rate_limiting.counter.complete.(com.gmail).(boramalper)
       email.rate_limiting.counter.complete.(com.hotmail).(fenasi.kerim)
       email.rate_limiting.counter.complete.(com.hotmail).(fena.sikerim)
       
   - __E-Mail Service Providers:__
   
     See `__whitelist` at [`email/address.py`](email/address.py).
       
   __Beware:__
   
   - GMail for instance (along with many other e-mail service providers) uses the part after
     `+` to tag e-mails, so `boramalper@gmail.com` and `boramalper+reis@gmail.com` are same.
     
   - GMail ignores periods in the username.
   
   - __Hence we might have to strip certain parts of the e-mail addresses!__
   
     See `normalise_local()` at [`email/address.py`](email/address.py).
     
- `email.rate_limiting.counter.nolocal.(<REVERSE DOMAIN>)`

  for domains that are not whitelisted.
  
  __For instance:__
  
      email.rate_limiting.counter.nolocal.(org.boramalper)
      
  whatever the username is...
