/** Encrypt one bounded research audit payload; never read environment credentials. */
import {createPublicKey,generateKeyPairSync,diffieHellman,hkdfSync,randomBytes,createCipheriv,createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

export const PROTOCOL='CILE-SEALED-AUDIT-1';
export function seal(payload,recipient,now=Date.now()) {
  if(!Buffer.isBuffer(payload)||payload.length>2000000)throw Error('audit_payload_limit');
  if(recipient.protocol!==PROTOCOL||!Number.isFinite(Date.parse(recipient.expires_at))||now>=Date.parse(recipient.expires_at))throw Error('audit_recipient_expired_or_invalid');
  const der=Buffer.from(recipient.public_key_spki,'base64');
  if(createHash('sha256').update(der).digest('hex')!==recipient.public_key_sha256)throw Error('audit_recipient_integrity');
  const publicKey=createPublicKey({key:der,type:'spki',format:'der'});
  if(publicKey.asymmetricKeyType!=='x25519')throw Error('audit_recipient_type');
  const ephemeral=generateKeyPairSync('x25519'),salt=randomBytes(32),nonce=randomBytes(12);
  const key=Buffer.from(hkdfSync('sha256',diffieHellman({privateKey:ephemeral.privateKey,publicKey}),salt,Buffer.from(PROTOCOL),32));
  const aad=Buffer.from(JSON.stringify({protocol:PROTOCOL,recipient_sha256:recipient.public_key_sha256}));
  const cipher=createCipheriv('aes-256-gcm',key,nonce,{authTagLength:16});cipher.setAAD(aad);
  const ciphertext=Buffer.concat([cipher.update(payload),cipher.final()]);key.fill(0);
  return {protocol:PROTOCOL,ephemeral_spki:ephemeral.publicKey.export({format:'der',type:'spki'}).toString('base64'),salt:salt.toString('base64'),nonce:nonce.toString('base64'),aad:aad.toString('base64'),ciphertext:ciphertext.toString('base64'),tag:cipher.getAuthTag().toString('base64')};
}
if(process.argv[1]===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==4)throw Error('audit_arguments');
    const recipient=JSON.parse(readFileSync(new URL('../../config/enrichment-audit-recipient.json',import.meta.url),'utf8'));
    const envelope=seal(readFileSync(process.argv[2]),recipient);
    writeFileSync(process.argv[3],JSON.stringify(envelope),{flag:'wx',mode:0o600});
  }catch{process.stderr.write('audit_sealing_failed\n');process.exitCode=1;}
}
